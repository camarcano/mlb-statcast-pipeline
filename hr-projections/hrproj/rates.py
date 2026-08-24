"""Per-batter true home run rate per plate appearance.

Three ingredients: recency-weighted playing history, a blend of actual and
expected home runs, and regression to the league mean. The output carries a Beta
posterior so the simulation can propagate each hitter's uncertainty instead of
treating a 40-PA call-up as being as well known as a 500-PA regular.
"""

from typing import Optional

import numpy as np
import pandas as pd

from hrproj.config import ModelParams
from hrproj.data import decay_weights


def batter_rates(
    pa: pd.DataFrame,
    xhr_per_pa: pd.Series,
    as_of: str,
    params: ModelParams,
    league_mu: Optional[float] = None,
) -> pd.DataFrame:
    """One row per batter: team, weighted exposure, blended HR, posterior rate.

    Columns: batter, player_name, team, pa, hr, xhr, w_pa, w_hr, w_xhr,
    blend, rate, alpha, beta, last_game.

    `league_mu` is the rate everyone regresses toward. It defaults to the
    recency-weighted league rate, but callers should normally pass the flat
    season-to-date rate: the league home run environment swings seasonally (it
    peaked in June 2026 and fell through August), and recency-weighting it
    projects the current month's weather forward into September.
    """
    if pa.empty:
        return pd.DataFrame(
            columns=[
                "batter", "player_name", "team", "pa", "hr", "xhr", "w_pa",
                "w_hr", "w_xhr", "blend", "rate", "alpha", "beta", "last_game",
            ]
        )

    df = pa.copy()
    df["w"] = decay_weights(df["game_date"], as_of, params.half_life_days)
    df["xhr"] = xhr_per_pa.to_numpy()
    df["w_hr"] = df["w"] * df["is_hr"]
    df["w_xhr"] = df["w"] * df["xhr"]

    grouped = df.groupby("batter")
    out = pd.DataFrame({
        "player_name": grouped["player_name"].last(),
        "pa": grouped.size(),
        "hr": grouped["is_hr"].sum(),
        "xhr": grouped["xhr"].sum(),
        "w_pa": grouped["w"].sum(),
        "w_hr": grouped["w_hr"].sum(),
        "w_xhr": grouped["w_xhr"].sum(),
        "last_game": grouped["game_date"].max(),
    })
    out["team"] = _current_team(df)

    if league_mu is None:
        league_mu = float(df["w_hr"].sum() / df["w"].sum())

    out["blend"] = params.phi * out["w_xhr"] + (1 - params.phi) * out["w_hr"]
    prior = params.k_pa * league_mu
    out["rate"] = (out["blend"] + prior) / (out["w_pa"] + params.k_pa)

    # Beta posterior: prior of k_pa pseudo-PA at the league rate, plus the
    # player's own blended evidence.
    out["alpha"] = np.maximum(out["blend"] + prior, 1e-6)
    out["beta"] = np.maximum(
        out["w_pa"] - out["blend"] + params.k_pa * (1 - league_mu), 1e-6
    )

    out = out.reset_index()
    out.attrs["league_mu"] = league_mu
    return out


def _current_team(df: pd.DataFrame) -> pd.Series:
    """A batter's team is the team of their most recent plate appearance."""
    ordered = df.sort_values("game_date")
    return ordered.groupby("batter")["bat_team"].last()


def league_hr_per_pa(pa: pd.DataFrame, as_of: str, params: ModelParams) -> float:
    if pa.empty:
        return 0.0
    w = decay_weights(pa["game_date"], as_of, params.half_life_days)
    return float((w * pa["is_hr"]).sum() / w.sum())
