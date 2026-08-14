"""Build pitch-grain features and the pitcher-family-year arsenal table.

Runs one season at a time so memory stays bounded, writing:
  data/analysis/pitches/game_year=YYYY/part.parquet   (pitch grain + features)
  data/analysis/arsenal.parquet                       (pitcher-family-year rows)
"""
from __future__ import annotations

import json
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import features as F
from analysis.lib import outcomes as oc

RAW_DIR = config.PARQUET_DIR / "raw"
OUT_DIR = config.PARQUET_DIR / "pitches"

KEEP = [
    "game_pk", "game_date", "game_year", "at_bat_number", "pitch_number",
    "pitcher", "batter", "player_name", "p_throws", "stand",
    "pitch_type", "family",
    "release_speed", "release_spin_rate", "spin_axis",
    "spin_axis_sin", "spin_axis_cos",
    "ivb", "hb_arm", "release_side_arm", "release_pos_z", "release_extension",
    "arm_angle", "plate_x", "plate_z", "zone",
    "balls", "strikes", "n_thruorder_pitcher", "inning",
    "description", "events", "type",
    "is_whiff", "is_swing", "is_called_strike", "is_csw", "is_bip", "in_zone",
    "launch_speed", "launch_angle",
    "estimated_woba_using_speedangle", "delta_run_exp", "delta_pitcher_run_exp",
    "cell_velo", "cell_ivb", "cell_hb", "cell_id",
]


def available_years() -> list[int]:
    return sorted(
        int(p.name.split("=")[1]) for p in RAW_DIR.glob("game_year=*") if p.is_dir()
    )


def main() -> None:
    years = available_years()
    if not years:
        raise SystemExit("no extracted data found; run 01_extract.py first")

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    manifest_path = config.RESULTS_DIR / "data_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    include_arm_angle = bool(manifest.get("arm_angle_in_feature_vector", False))

    sign_checks, counts = [], []
    for year in years:
        df = pd.read_parquet(RAW_DIR / f"game_year={year}")
        df["game_year"] = year
        df = F.add_shape_features(df)
        df = df[df["family"].notna()].copy()
        df = oc.add_outcome_flags(df)
        df = F.add_shape_cells(df)

        sign = F.check_handedness_sign(df)
        sign["game_year"] = year
        sign_checks.append(sign)

        out = df[[c for c in KEEP if c in df.columns]]
        (OUT_DIR / f"game_year={year}").mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT_DIR / f"game_year={year}" / "part.parquet", index=False)
        counts.append({"game_year": year, "pitches": len(out)})
        print(f"{year}: {len(out):,} classified pitches  "
              f"(sinker arm-side break R={sign['sinker_hb_arm_mean_R']:.1f}\" "
              f"L={sign['sinker_hb_arm_mean_L']:.1f}\")")
        del df, out

    sign_df = pd.DataFrame(sign_checks)
    if not sign_df["passed"].all():
        raise SystemExit(
            "FATAL: handedness sign check failed -- sinkers must show strong "
            "positive arm-side break for both hands. Horizontal features are "
            "mis-signed; fix add_shape_features before continuing.\n"
            + sign_df.to_string(index=False)
        )
    D.save_result(sign_df, "s0_handedness_check")

    # --- arsenal rows -------------------------------------------------------
    feats = list(config.SHAPE_FEATURES) + (["arm_angle"] if include_arm_angle else [])
    frames = []
    for year in years:
        d = pd.read_parquet(OUT_DIR / f"game_year={year}")
        frames.append(F.build_arsenal_rows(d, feats))
        del d
    arsenal = pd.concat(frames, ignore_index=True)
    arsenal.to_parquet(D.arsenal_path(), index=False)

    # pooled scaling for cross-year comparability
    scaling = F.fit_scaling(arsenal, feats, by="family")
    F.save_scaling(scaling)

    print(f"\narsenal rows (>= {config.MIN_PITCHES_ARSENAL} pitches): {len(arsenal):,}")
    print(arsenal.groupby("game_year").size().to_string())

    D.write_meta("s2_features", {
        "years": years,
        "pitch_counts": counts,
        "arsenal_rows": int(len(arsenal)),
        "shape_features": feats,
        "arm_angle_included": include_arm_angle,
        "handedness_check": sign_df.to_dict(orient="records"),
    })


if __name__ == "__main__":
    main()
