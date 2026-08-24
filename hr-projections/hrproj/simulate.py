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

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from hrproj.model import Projection


@dataclass
class SimulationResult:
    totals: pd.DataFrame        # one row per team, summary columns
    draws: dict[str, np.ndarray]  # team -> array of simulated final HR totals
    sims: int
    seed: int
    players: pd.DataFrame = field(default_factory=pd.DataFrame)


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

    player_frames: list[pd.DataFrame] = []

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

        # Plate appearances available to the whole club across the games left,
        # scaled by the park and pitching it faces, then split between hitters.
        team_pa = ti.pa_per_game * ti.context_sum * environment
        player_lam = share_draws * rate_draws * team_pa[:, None]
        player_hr = rng.poisson(np.maximum(player_lam, 0.0))

        # A team's remaining home runs are its hitters' - drawn once, so the two
        # views of the same simulation cannot contradict each other.
        draws[team] = ti.hr_to_date + player_hr.sum(axis=1)
        player_frames.append(_summarise_players(ti, player_hr, share_draws, params))

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

    players = (
        pd.concat(player_frames, ignore_index=True)
        if player_frames
        else pd.DataFrame()
    )
    if not players.empty:
        players = players.sort_values("projected", ascending=False).reset_index(drop=True)

    return SimulationResult(
        totals=totals, draws=draws, sims=sims, seed=params.seed, players=players
    )


def _summarise_players(
    ti, player_hr: np.ndarray, share_draws: np.ndarray, params
) -> pd.DataFrame:
    """Reduce one team's per-hitter draws to a row each.

    The draws are summarised here rather than returned: keeping every simulation
    for every hitter in memory buys nothing once the percentiles are known.
    """
    hr_to_date = ti.batters["hr"].fillna(0).to_numpy(dtype=float)
    finals = hr_to_date[None, :] + player_hr

    summary = pd.DataFrame({
        "team": ti.team,
        "batter": ti.batters["batter"].to_numpy(),
        "player_name": ti.batters["player_name"].to_numpy(),
        "hr_to_date": hr_to_date.astype(int),
        "pa": ti.batters["pa"].fillna(0).to_numpy(),
        "xhr": ti.batters["xhr"].fillna(0).to_numpy(),
        "rate": ti.batters["rate"].to_numpy(),
        "games_remaining": ti.games_remaining,
        "proj_pa": share_draws.mean(axis=0) * ti.pa_per_game * ti.games_remaining,
        "expected_remaining": player_hr.mean(axis=0),
        "projected": finals.mean(axis=0),
        "p10": np.percentile(finals, 10, axis=0),
        "median": np.percentile(finals, 50, axis=0),
        "p90": np.percentile(finals, 90, axis=0),
    })

    for milestone in params.hr_milestones:
        summary[f"p_{milestone}"] = (finals >= milestone).mean(axis=0)

    return summary


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
