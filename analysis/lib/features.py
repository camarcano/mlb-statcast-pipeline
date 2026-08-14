"""Pitch-shape feature engineering.

Two conventions matter throughout:

* Movement is expressed in inches (Savant's pfx_x/pfx_z are feet).
* Horizontal quantities are handedness-normalised so that positive always
  means arm-side. Without this, pooling LHP and RHP would manufacture
  bimodality in every horizontal feature and destroy the dispersion analysis.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from analysis import config
from analysis.lib import taxonomy


def add_shape_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive IVB, arm-side break, arm-side release and spin-axis components."""
    d = df
    hand_sign = np.where(d["p_throws"].eq("R"), 1.0, -1.0)

    d["ivb"] = 12.0 * pd.to_numeric(d["pfx_z"], errors="coerce")
    # pfx_x is catcher-perspective: negative = toward third base. For a RHP,
    # arm-side run is toward first base, i.e. negative pfx_x -- hence the flip.
    d["hb_arm"] = -12.0 * pd.to_numeric(d["pfx_x"], errors="coerce") * hand_sign
    d["release_side_arm"] = -pd.to_numeric(d["release_pos_x"], errors="coerce") * hand_sign

    axis = pd.to_numeric(d["spin_axis"], errors="coerce")
    rad = np.deg2rad(axis)
    d["spin_axis_sin"] = np.sin(rad)
    d["spin_axis_cos"] = np.cos(rad)

    d["family"] = taxonomy.assign_family(d["pitch_type"])
    return d


def check_handedness_sign(df: pd.DataFrame) -> dict:
    """Sanity gate: sinkers must show strong positive arm-side break for both hands.

    A failure here means the sign convention is inverted and every horizontal
    result downstream would be wrong, so callers should treat it as fatal.
    """
    out = {}
    si = df[df["family"] == "SI"]
    for hand in ("R", "L"):
        sub = si[si["p_throws"] == hand]["hb_arm"].dropna()
        out[f"sinker_hb_arm_mean_{hand}"] = float(sub.mean()) if len(sub) else np.nan
    ok = all(
        np.isfinite(v) and v > 5.0
        for k, v in out.items() if k.startswith("sinker_hb_arm_mean")
    )
    out["passed"] = bool(ok)
    return out


def available_shape_features(df: pd.DataFrame,
                             include_arm_angle: bool | None = None) -> list[str]:
    """The shape vector, with arm_angle appended only if coverage allows."""
    feats = list(config.SHAPE_FEATURES)
    if include_arm_angle is None:
        include_arm_angle = arm_angle_coverage_ok(df)
    if include_arm_angle and "arm_angle" in df.columns:
        feats.append("arm_angle")
    return feats


def arm_angle_coverage_ok(df: pd.DataFrame) -> bool:
    if "arm_angle" not in df.columns:
        return False
    cov = df.groupby("game_year")["arm_angle"].apply(lambda s: s.notna().mean())
    return bool((cov >= config.ARM_ANGLE_COVERAGE_MIN).all())


# --------------------------------------------------------------------------
# standardisation
# --------------------------------------------------------------------------
def fit_scaling(df: pd.DataFrame, features: list[str],
                by: str = "family") -> dict:
    """Pooled (all-years) robust centre/scale per family, so that year-to-year
    dispersion comparisons are expressed in a single fixed metric."""
    scaling = {}
    for key, sub in df.groupby(by, dropna=True):
        scaling[str(key)] = {
            f: {
                "center": float(sub[f].median(skipna=True)),
                "scale": float(
                    max(np.nanmedian(np.abs(sub[f] - sub[f].median())) * 1.4826, 1e-6)
                ),
            }
            for f in features if f in sub.columns
        }
    return scaling


def save_scaling(scaling: dict, path=None) -> None:
    path = path or (config.RESULTS_DIR / "scaling.json")
    path.write_text(json.dumps(scaling, indent=2))


def load_scaling(path=None) -> dict:
    path = path or (config.RESULTS_DIR / "scaling.json")
    return json.loads(path.read_text())


def apply_scaling(df: pd.DataFrame, features: list[str], scaling: dict,
                  by: str = "family") -> pd.DataFrame:
    """Return a z-scored copy of `features` using a stored scaling dict."""
    out = df.copy()
    for key, sub_idx in df.groupby(by, dropna=True).groups.items():
        params = scaling.get(str(key))
        if not params:
            continue
        for f in features:
            if f in params and f in out.columns:
                p = params[f]
                out.loc[sub_idx, f] = (df.loc[sub_idx, f] - p["center"]) / p["scale"]
    return out


def standardize_within(df: pd.DataFrame, features: list[str],
                       group_cols: list[str]) -> pd.DataFrame:
    """Robust z-scores computed within each group (used for same-year scaling)."""
    out = df.copy()
    for f in features:
        g = out.groupby(group_cols)[f]
        med = g.transform("median")
        mad = g.transform(lambda s: np.nanmedian(np.abs(s - np.nanmedian(s))) * 1.4826)
        out[f] = (out[f] - med) / mad.replace(0, np.nan)
    return out


# --------------------------------------------------------------------------
# arsenal rows: the primary analysis grain
# --------------------------------------------------------------------------
def build_arsenal_rows(pitches: pd.DataFrame, features: list[str],
                       min_pitches: int = config.MIN_PITCHES_ARSENAL) -> pd.DataFrame:
    """Collapse pitches to one row per (pitcher, family, year).

    This is the unit at which a "pitch" exists as a designed object: a pitcher's
    slider in 2024 is one thing, thrown many times. Working at this grain stops
    high-usage pitchers from dominating league dispersion estimates.
    """
    from analysis.lib import outcomes as oc

    keys = ["pitcher", "family", "game_year"]
    g = pitches.groupby(keys, dropna=True)

    centroids = g[features].median()
    tallies = oc.aggregate_outcomes(pitches, keys).set_index(keys)

    meta = pd.DataFrame({
        # NOTE: Savant's player_name is the *batter* on these rows, not the
        # pitcher, so it is deliberately not carried onto arsenal rows. Pitcher
        # names come from data/pitcher_names.json via pitcher_name_map().
        "p_throws": g["p_throws"].first(),
        "spin_axis_sin": g["spin_axis_sin"].mean(),
        "spin_axis_cos": g["spin_axis_cos"].mean(),
        "platoon_share": g.apply(
            lambda s: float((s["stand"] != s["p_throws"]).mean()),
            include_groups=False,
        ),
    })

    ars = centroids.join(meta).join(tallies)
    ars = ars.reset_index()

    # usage share within the pitcher-year
    py_total = ars.groupby(["pitcher", "game_year"])["pitches"].transform("sum")
    ars["pitcher_year_pitches"] = py_total
    ars["usage_share"] = ars["pitches"] / py_total

    ars = ars[ars["pitches"] >= min_pitches].copy()
    ars["spin_axis_deg"] = np.rad2deg(
        np.arctan2(ars["spin_axis_sin"], ars["spin_axis_cos"])
    ) % 360
    return ars


# --------------------------------------------------------------------------
# shape cells (S6 / S7)
# --------------------------------------------------------------------------
def add_shape_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Discretise the shape space into velocity x IVB x HB cells."""
    d = df
    d["cell_velo"] = np.floor(d["release_speed"] / config.CELL_VELO_BIN)
    d["cell_ivb"] = np.floor(d["ivb"] / config.CELL_IVB_BIN)
    d["cell_hb"] = np.floor(d["hb_arm"] / config.CELL_HB_BIN)
    d["cell_id"] = (
        d["family"].astype(str) + "|"
        + d["cell_velo"].astype("Int64").astype(str) + "|"
        + d["cell_ivb"].astype("Int64").astype(str) + "|"
        + d["cell_hb"].astype("Int64").astype(str)
    )
    return d
