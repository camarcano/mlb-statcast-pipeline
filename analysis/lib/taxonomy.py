"""Pitch-type taxonomy handling.

Savant's pitch classifier is not stable across seasons: the sweeper (ST) and
slurve (SV) codes were introduced for 2023 out of what had previously been
labelled SL. Any trend computed on raw `pitch_type` therefore mixes a real
behavioural change with a relabelling artefact. All primary analyses run on
stable families defined in config.PITCH_FAMILIES; fine-grained types are used
only where 00_validate_data.py shows the labels are usable.
"""
from __future__ import annotations

import pandas as pd

from analysis import config


def assign_family(pitch_type: pd.Series) -> pd.Series:
    """Map Savant pitch_type codes to stable families; unknown codes -> NA."""
    return pitch_type.map(config.PITCH_FAMILIES).astype("object")


def label(family: str) -> str:
    return config.FAMILY_LABELS.get(family, family)


def stability_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per pitch_type x year share, used to document classifier drift.

    Expects columns `pitch_type` and `game_year`.
    """
    counts = (
        df.groupby(["game_year", "pitch_type"], dropna=False)
        .size().rename("pitches").reset_index()
    )
    totals = counts.groupby("game_year")["pitches"].transform("sum")
    counts["share_pct"] = 100 * counts["pitches"] / totals
    wide = counts.pivot(index="pitch_type", columns="game_year",
                        values="share_pct").fillna(0.0).round(3)
    wide["max_abs_yoy_change"] = wide.diff(axis=1).abs().max(axis=1).round(3)
    return wide.reset_index()


def sweeper_labels_are_retroactive(stability: pd.DataFrame,
                                   min_share: float = 0.5) -> bool:
    """True if ST appears with a plausible share in every season.

    When Savant re-classifies history, ST exists back to 2021 and per-type
    sweeper analysis is legitimate. When it only appears from 2023, sweeper
    questions must be answered at the slider-family level instead.
    """
    row = stability[stability["pitch_type"] == "ST"]
    if row.empty:
        return False
    years = [c for c in stability.columns if isinstance(c, (int,)) or str(c).isdigit()]
    vals = [float(row.iloc[0][y]) for y in years]
    return all(v >= min_share for v in vals)
