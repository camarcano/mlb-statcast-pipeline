"""Assembling the projection inputs: who bats, how often, and against what.

`build_projection` turns a Statcast frame plus a remaining schedule into the
arrays the simulator consumes. The per-game expected rate is

    lambda_g = PA_per_game(team) * sum_i share_i * rate_i * park_g * opponent_g

and because independent Poisson draws add, the simulator only needs each team's
summed context multiplier rather than the game-by-game breakdown.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from hrproj import park as park_mod
from hrproj import playing_time as pt_mod
from hrproj import rates as rates_mod
from hrproj import xhr as xhr_mod
from hrproj.config import ModelParams
from hrproj.data import team_games_played, team_hr_to_date


@dataclass
class TeamInputs:
    team: str
    hr_to_date: int
    games_played: int
    games_remaining: int
    context_sum: float           # sum over remaining games of park * opponent
    pa_per_game: float
    batters: pd.DataFrame        # batter, player_name, share, rate, alpha, beta, concentration

    @property
    def point_rate(self) -> float:
        if self.batters.empty:
            return 0.0
        return float((self.batters["share"] * self.batters["rate"]).sum())

    @property
    def expected_remaining(self) -> float:
        return self.point_rate * self.pa_per_game * self.context_sum

    @property
    def projected(self) -> float:
        return self.hr_to_date + self.expected_remaining


@dataclass
class Projection:
    as_of: str
    season: int
    teams: dict[str, TeamInputs]
    league_hr_per_pa: float
    park_factors: pd.Series
    opponent_factors: pd.Series
    batter_rates: pd.DataFrame
    params: ModelParams
    normalization: float = 1.0
    schedule_source: str = "statsapi"
    warnings: list[str] = field(default_factory=list)


def build_projection(
    pa: pd.DataFrame,
    remaining: list[dict],
    as_of: str,
    season: int,
    params: ModelParams,
    schedule_source: str = "statsapi",
    xhr_per_pa: Optional[pd.Series] = None,
) -> Projection:
    """Combine contact, playing time and schedule context into per-team inputs.

    `xhr_per_pa` may be supplied to reuse a grid across repeated fits (the
    backtest sweep does this - the grid depends on none of the swept constants).
    """
    warnings: list[str] = []

    if xhr_per_pa is None:
        grid = xhr_mod.build_grid(pa[pa["is_bbe"]], params)
        xhr_per_pa = xhr_mod.expected_hr_per_pa(pa, grid)

    # The league anchor is the flat season-to-date rate, not a recency-weighted
    # one: the league's home run environment moves with the weather, and the
    # season average is the better guess at what the remaining games will look
    # like. Recency weighting still shapes the differences between hitters.
    league_flat = float(pa["is_hr"].mean())
    rate_df = rates_mod.batter_rates(pa, xhr_per_pa, as_of, params, league_mu=league_flat)
    league_mu = league_flat

    shares = pt_mod.batter_shares(pa, as_of, params)
    pa_per_game = pt_mod.team_pa_per_game(pa, params)

    parks = park_mod.park_factors(pa, params) if params.use_park else pd.Series(dtype=float)
    opps = (
        park_mod.opponent_factors(pa, parks, params)
        if params.use_opponent
        else pd.Series(dtype=float)
    )

    hr_to_date = team_hr_to_date(pa)
    games_played = team_games_played(pa)

    context = _context_by_team(remaining, parks, opps, params)

    teams: dict[str, TeamInputs] = {}
    for team in sorted(games_played.index):
        team_shares = shares[shares["team"] == team]
        batters = team_shares.merge(
            rate_df[["batter", "player_name", "rate", "alpha", "beta", "pa", "hr", "xhr"]],
            on="batter",
            how="left",
        )
        missing = batters["rate"].isna()
        if missing.any():
            batters.loc[missing, ["rate", "alpha", "beta"]] = [
                league_mu, params.k_pa * league_mu, params.k_pa * (1 - league_mu)
            ]

        n_games, ctx_sum = context.get(team, (0, 0.0))
        if n_games == 0:
            warnings.append(f"{team}: no remaining games found")
        if batters.empty and n_games > 0:
            warnings.append(
                f"{team}: no hitters with recent plate appearances - "
                "projecting no further home runs (check the database for gaps)"
            )

        teams[team] = TeamInputs(
            team=team,
            hr_to_date=int(hr_to_date.get(team, 0)),
            games_played=int(games_played.get(team, 0)),
            games_remaining=n_games,
            context_sum=ctx_sum,
            pa_per_game=float(pa_per_game.get(team, 0.0)),
            batters=batters,
        )

    scale = _league_scale(teams, league_mu) if params.league_normalize else 1.0
    if scale != 1.0:
        for ti in teams.values():
            _rescale(ti.batters, scale)

    return Projection(
        as_of=as_of,
        season=season,
        teams=teams,
        league_hr_per_pa=league_mu,
        park_factors=parks,
        opponent_factors=opps,
        batter_rates=rate_df,
        params=params,
        normalization=scale,
        schedule_source=schedule_source,
        warnings=warnings,
    )


def _league_scale(teams: dict[str, "TeamInputs"], league_mu: float) -> float:
    """Factor that pulls the league-wide projected rate back onto the league rate.

    Playing-time shares concentrate on hitters currently in the lineup, and those
    hitters out-homer the all-plate-appearance average that `league_mu` measures.
    Left alone, every team's projection inherits that gap - about +3.5% in 2026,
    which is a couple of home runs per club over a season's final month. Scaling
    every rate by one league-wide factor removes the aggregate bias while leaving
    the differences between clubs untouched.
    """
    weight = sum(ti.pa_per_game for ti in teams.values())
    if weight <= 0 or league_mu <= 0:
        return 1.0

    projected = sum(ti.point_rate * ti.pa_per_game for ti in teams.values()) / weight
    if projected <= 0:
        return 1.0
    return league_mu / projected


def _rescale(batters: pd.DataFrame, scale: float) -> None:
    """Scale rates by `scale`, keeping each posterior's effective sample size."""
    if batters.empty:
        return
    n = batters["alpha"] + batters["beta"]
    batters["rate"] = batters["rate"] * scale
    batters["alpha"] = np.maximum(batters["alpha"] * scale, 1e-6)
    batters["beta"] = np.maximum(n - batters["alpha"], 1e-6)


def _context_by_team(
    remaining: list[dict],
    parks: pd.Series,
    opps: pd.Series,
    params: ModelParams,
) -> dict[str, tuple[int, float]]:
    """Per team: number of remaining games and the summed park*opponent multiplier."""
    counts: dict[str, int] = {}
    sums: dict[str, float] = {}

    for game in remaining:
        team = game["team"]
        factor = 1.0

        if params.use_park:
            venue_team = game.get("venue_team")
            if venue_team is not None and len(parks):
                factor *= float(parks.get(venue_team, 1.0))

        if params.use_opponent:
            opponent = game.get("opponent")
            if opponent is not None and len(opps):
                factor *= float(opps.get(opponent, 1.0))

        counts[team] = counts.get(team, 0) + 1
        sums[team] = sums.get(team, 0.0) + factor

    return {t: (counts[t], sums[t]) for t in counts}
