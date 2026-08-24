"""Monte Carlo over the remaining schedule.

Three sources of uncertainty are carried, not just one:

* each hitter's true rate, drawn from their Beta posterior;
* playing time, drawn from a Dirichlet whose concentration scales with how much
  recent evidence there is (a settled lineup moves less than a churning one);
* the league home run environment, one factor shared by all 30 clubs;
* the games themselves, Poisson around the resulting rate.

Independent Poisson draws add, so a team's remaining home runs can be drawn once
from the season-total rate rather than game by game.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hrproj.model import Projection


@dataclass
class SimulationResult:
    totals: pd.DataFrame        # one row per team, summary columns
    draws: dict[str, np.ndarray]  # team -> array of simulated final HR totals
    sims: int
    seed: int


def simulate(projection: Projection) -> SimulationResult:
    params = projection.params
    rng = np.random.default_rng(params.seed)
    sims = params.sims

    teams = sorted(projection.teams)
    draws: dict[str, np.ndarray] = {}

    # One environment factor per simulation, shared across teams: whether the
    # last month of the season plays hot or cold happens to everyone at once.
    if params.league_env_sd > 0:
        sigma = params.league_env_sd
        environment = rng.lognormal(-0.5 * sigma ** 2, sigma, size=sims)
    else:
        environment = np.ones(sims)

    for team in teams:
        ti = projection.teams[team]
        if ti.batters.empty or ti.games_remaining == 0:
            draws[team] = np.full(sims, float(ti.hr_to_date))
            continue

        alpha = ti.batters["alpha"].to_numpy(dtype=float)
        beta = ti.batters["beta"].to_numpy(dtype=float)
        share = ti.batters["share"].to_numpy(dtype=float)
        concentration = float(ti.batters["concentration"].iloc[0])

        rate_draws = rng.beta(alpha, beta, size=(sims, len(alpha)))
        share_draws = rng.dirichlet(np.maximum(share * concentration, 1e-3), size=sims)

        team_rate = (rate_draws * share_draws).sum(axis=1)
        lam = team_rate * ti.pa_per_game * ti.context_sum * environment
        draws[team] = ti.hr_to_date + rng.poisson(np.maximum(lam, 0.0))

    matrix = np.column_stack([draws[t] for t in teams])
    lead_prob = _leader_probability(matrix)
    top3_prob = _top_n_probability(matrix, 3)

    current = np.array([projection.teams[t].hr_to_date for t in teams], dtype=float)
    projected_mean = matrix.mean(axis=0)
    order = (-projected_mean).argsort().argsort() + 1
    current_rank = (-current).argsort().argsort() + 1

    totals = pd.DataFrame({
        "team": teams,
        "hr_to_date": current.astype(int),
        "games_remaining": [projection.teams[t].games_remaining for t in teams],
        "expected_remaining": [projection.teams[t].expected_remaining for t in teams],
        "projected": projected_mean,
        "p10": np.percentile(matrix, 10, axis=0),
        "median": np.percentile(matrix, 50, axis=0),
        "p90": np.percentile(matrix, 90, axis=0),
        "p_lead": lead_prob,
        "p_top3": top3_prob,
        "current_rank": current_rank,
        "projected_rank": order,
    }).sort_values("projected", ascending=False).reset_index(drop=True)

    return SimulationResult(totals=totals, draws=draws, sims=sims, seed=params.seed)


def _leader_probability(matrix: np.ndarray) -> np.ndarray:
    """P(team finishes with the most home runs), splitting ties evenly."""
    best = matrix.max(axis=1, keepdims=True)
    winners = matrix == best
    return (winners / winners.sum(axis=1, keepdims=True)).mean(axis=0)


def _top_n_probability(matrix: np.ndarray, n: int) -> np.ndarray:
    """P(team finishes in the top n), ties resolved by shared credit for the cut."""
    sims, n_teams = matrix.shape
    if n >= n_teams:
        return np.ones(n_teams)

    # Threshold is the nth best total in each sim.
    threshold = -np.partition(-matrix, n - 1, axis=1)[:, n - 1][:, None]
    above = matrix > threshold
    tied = matrix == threshold
    slots_left = n - above.sum(axis=1, keepdims=True)
    tie_credit = np.where(tied, slots_left / np.maximum(tied.sum(axis=1, keepdims=True), 1), 0.0)
    return (above + tie_credit).mean(axis=0)
