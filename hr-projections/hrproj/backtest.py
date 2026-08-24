"""Out-of-sample scoring: does this model beat the obvious alternatives?

Fit on data through a cutoff, project the games that were actually played after
it, compare with what happened. The actual game log stands in for the schedule so
the test measures the rate model rather than schedule retrieval.

Baselines are deliberately the things a reasonable person would do instead:
extrapolate the team's home runs per game, extrapolate its expected home runs per
game, or regress everyone to the league rate. A model that cannot beat all three
is not earning its complexity, and the sweep will say so.
"""

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from hrproj import xhr as xhr_mod
from hrproj.config import ModelParams
from hrproj.model import build_projection


@dataclass
class BacktestResult:
    cutoff: str
    end: str
    per_team: pd.DataFrame
    scores: pd.DataFrame
    params: ModelParams


def schedule_from_played(test: pd.DataFrame) -> list[dict]:
    """Turn games that were actually played into the schedule shape the model reads."""
    games = test[["game_pk", "game_date", "bat_team", "pitch_team", "home_team"]].drop_duplicates(
        subset=["game_pk", "bat_team"]
    )
    return [
        {
            "game_pk": row.game_pk,
            "game_date": str(row.game_date.date()) if hasattr(row.game_date, "date") else row.game_date,
            "team": row.bat_team,
            "opponent": row.pitch_team,
            "home": row.bat_team == row.home_team,
            "venue_team": row.home_team,
        }
        for row in games.itertuples()
    ]


def run_backtest(
    pa: pd.DataFrame,
    cutoff: str,
    end: str,
    season: int,
    params: ModelParams,
    xhr_train: Optional[pd.Series] = None,
) -> BacktestResult:
    cutoff_ts = pd.Timestamp(cutoff)
    end_ts = pd.Timestamp(end)

    train = pa[pa["game_date"] <= cutoff_ts]
    test = pa[(pa["game_date"] > cutoff_ts) & (pa["game_date"] <= end_ts)]
    if train.empty or test.empty:
        raise ValueError(f"No data on one side of the cutoff ({cutoff}).")

    if xhr_train is None:
        xhr_train = xhr_mod.expected_hr_feature(train, params)

    remaining = schedule_from_played(test)
    projection = build_projection(
        train, remaining, cutoff, season, params,
        schedule_source="actual-game-log", xhr_per_pa=xhr_train,
    )

    actual = test.groupby("bat_team")["is_hr"].sum()
    games = test.groupby("bat_team")["game_pk"].nunique()

    train_hr = train.groupby("bat_team")["is_hr"].sum()
    train_games = train.groupby("bat_team")["game_pk"].nunique()
    train_xhr = (
        pd.Series(xhr_train.to_numpy(), index=train.index)
        .groupby(train["bat_team"]).sum()
    )
    league_rate = float(train_hr.sum() / train_games.sum())

    rows = []
    for team in sorted(projection.teams):
        n_games = int(games.get(team, 0))
        rows.append({
            "team": team,
            "games": n_games,
            "actual": float(actual.get(team, 0.0)),
            "model": projection.teams[team].expected_remaining,
            "hr_per_game": float(train_hr.get(team, 0)) / max(1, int(train_games.get(team, 1))) * n_games,
            "xhr_per_game": float(train_xhr.get(team, 0)) / max(1, int(train_games.get(team, 1))) * n_games,
            "league": league_rate * n_games,
        })

    per_team = pd.DataFrame(rows)
    scores = score(per_team, ["model", "hr_per_game", "xhr_per_game", "league"])

    return BacktestResult(cutoff=cutoff, end=end, per_team=per_team, scores=scores, params=params)


def score(per_team: pd.DataFrame, methods: Iterable[str]) -> pd.DataFrame:
    rows = []
    for method in methods:
        err = per_team[method] - per_team["actual"]
        rows.append({
            "method": method,
            "mae": float(np.abs(err).mean()),
            "rmse": float(np.sqrt((err ** 2).mean())),
            "bias": float(err.mean()),
            "worst": float(np.abs(err).max()),
        })
    return pd.DataFrame(rows).sort_values("mae").reset_index(drop=True)


def sweep(
    pa: pd.DataFrame,
    cutoff: str,
    end: str,
    season: int,
    base: ModelParams,
    half_lives: Iterable[float] = (25, 45, 75, 120),
    phis: Iterable[float] = (0.0, 0.3, 0.5, 0.6, 0.8, 1.0),
    ks: Iterable[float] = (80, 130, 170, 250, 400),
    bbia_weights: Iterable[float] = (0.0,),
) -> pd.DataFrame:
    """Grid over the rate constants.

    The expensive pieces - the xHR grid and the BBIA100 estimator - are built once
    per BBIA weight and reused across every other combination, since none of the
    swept constants change them.
    """
    cutoff_ts = pd.Timestamp(cutoff)
    train = pa[pa["game_date"] <= cutoff_ts]
    grid = xhr_mod.build_grid(train[train["is_bbe"]], base)
    grid_xhr = xhr_mod.expected_hr_per_pa(train, grid)
    bbia_xhr = xhr_mod.bbia_expected_hr(train, xhr_mod.league_hr_per_bbia(train))

    rows = []
    for weight in bbia_weights:
        feature = xhr_mod.blend_features(grid_xhr, bbia_xhr, weight)
        for half_life, phi, k in product(half_lives, phis, ks):
            params = base.replace(
                half_life_days=half_life, phi=phi, k_pa=k, bbia_weight=weight
            )
            result = run_backtest(pa, cutoff, end, season, params, xhr_train=feature)
            model_score = result.scores[result.scores["method"] == "model"].iloc[0]
            rows.append({
                "half_life": half_life,
                "phi": phi,
                "k_pa": k,
                "bbia": weight,
                "mae": model_score["mae"],
                "rmse": model_score["rmse"],
                "bias": model_score["bias"],
            })

    return pd.DataFrame(rows).sort_values("mae").reset_index(drop=True)
