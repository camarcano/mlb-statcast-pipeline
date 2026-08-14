"""Pitch outcome definitions.

CSW and whiff follow the conventions already used by the repo's pitcher
leaderboard (webapp/pitcher/calculations.py): CSW = (called strikes + whiffs)
/ total pitches. Run value is expressed from the pitcher's perspective so that
higher is always better for the pitcher.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis import config


def add_outcome_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Attach boolean outcome columns to a pitch-grain frame."""
    d = df
    desc = d["description"].fillna("")
    d["is_whiff"] = desc.isin(config.WHIFF_DESCRIPTIONS)
    d["is_swing"] = desc.isin(config.SWING_DESCRIPTIONS)
    d["is_called_strike"] = desc.isin(config.CALLED_STRIKE_DESCRIPTIONS)
    d["is_csw"] = d["is_whiff"] | d["is_called_strike"]
    d["is_bip"] = d["type"].fillna("") == "X"
    d["in_zone"] = d["zone"].between(1, 9)
    return d


def rv100_pitcher(delta_run_exp: pd.Series) -> float:
    """Run value per 100 pitches, pitcher perspective (positive = good).

    Savant's delta_run_exp is signed from the batting team's perspective, so it
    is negated here.
    """
    x = pd.to_numeric(delta_run_exp, errors="coerce").dropna()
    if x.empty:
        return np.nan
    return float(-100.0 * x.mean())


def aggregate_outcomes(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Outcome tallies and rates for arbitrary grouping keys."""
    g = df.groupby(by, dropna=False)
    out = pd.DataFrame({
        "pitches": g.size(),
        "whiffs": g["is_whiff"].sum(),
        "swings": g["is_swing"].sum(),
        "called_strikes": g["is_called_strike"].sum(),
        "csw": g["is_csw"].sum(),
        "bip": g["is_bip"].sum(),
        "in_zone": g["in_zone"].sum(),
        "sum_dre": g["delta_run_exp"].sum(),
        "n_dre": g["delta_run_exp"].count(),
        "sum_xwoba": g["estimated_woba_using_speedangle"].sum(),
        "n_xwoba": g["estimated_woba_using_speedangle"].count(),
    })
    out["whiff_pct"] = 100 * out["whiffs"] / out["swings"].replace(0, np.nan)
    out["csw_pct"] = 100 * out["csw"] / out["pitches"]
    out["zone_pct"] = 100 * out["in_zone"] / out["pitches"]
    out["rv100"] = -100.0 * out["sum_dre"] / out["n_dre"].replace(0, np.nan)
    out["xwobacon"] = out["sum_xwoba"] / out["n_xwoba"].replace(0, np.nan)
    return out.reset_index()


OUTCOME_COLUMNS = ["whiff_pct", "csw_pct", "rv100", "xwobacon"]
OUTCOME_LABELS = {
    "whiff_pct": "Whiff% (per swing)",
    "csw_pct": "CSW%",
    "rv100": "Run value / 100 (pitcher)",
    "xwobacon": "xwOBA on contact",
}
# Direction in which "better for the pitcher" points.
OUTCOME_SIGN = {"whiff_pct": +1, "csw_pct": +1, "rv100": +1, "xwobacon": -1}
