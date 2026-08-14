"""Validate the ingested Statcast data and settle two design-gating questions.

1. arm_angle coverage per season -- decides whether arm angle joins the shape
   feature vector or stays descriptive.
2. Whether Savant's sweeper (ST) label exists retroactively in 2021-22 -- decides
   whether sweepers can be analysed as their own pitch type or only inside the
   slider family.

Also writes the data manifest that pins every downstream result to a specific
snapshot of the database.
"""
from __future__ import annotations

import json
import sys

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import taxonomy

PHYSICS_COLS = [
    "release_speed", "release_spin_rate", "spin_axis", "pfx_x", "pfx_z",
    "release_pos_x", "release_pos_z", "release_extension", "arm_angle",
    "plate_x", "plate_z", "delta_run_exp", "estimated_woba_using_speedangle",
    "bat_speed",
]


def main() -> None:
    con = D.connect()
    D.attach_sqlite(con)

    base = ("FROM savant.statcast_pitches WHERE game_type = 'R' "
            f"AND game_year BETWEEN {min(config.YEARS)} AND {max(config.YEARS)}")

    per_year = con.execute(f"""
        SELECT game_year,
               COUNT(*) AS pitches,
               COUNT(DISTINCT game_pk) AS games,
               COUNT(DISTINCT game_date) AS game_dates,
               MIN(game_date) AS first_date,
               MAX(game_date) AS last_date,
               COUNT(DISTINCT pitcher) AS pitchers
        {base} GROUP BY 1 ORDER BY 1
    """).df()
    print("\n=== rows per season ===")
    print(per_year.to_string(index=False))

    # --- null-rate table for every physics column, per season ---------------
    null_exprs = ", ".join(
        f"1.0 - (COUNT({c}) * 1.0 / COUNT(*)) AS null_{c}" for c in PHYSICS_COLS
    )
    nulls = con.execute(f"SELECT game_year, {null_exprs} {base} GROUP BY 1 ORDER BY 1").df()
    nulls_long = nulls.melt(id_vars="game_year", var_name="column",
                            value_name="null_rate")
    nulls_long["column"] = nulls_long["column"].str.replace("null_", "", regex=False)
    nulls_long["null_rate"] = nulls_long["null_rate"].round(4)
    print("\n=== arm_angle / bat_speed coverage by season ===")
    gate = nulls_long[nulls_long["column"].isin(["arm_angle", "bat_speed"])]
    print(gate.pivot(index="column", columns="game_year",
                     values="null_rate").to_string())

    arm_cov = (
        1 - nulls_long[nulls_long["column"] == "arm_angle"]
        .set_index("game_year")["null_rate"]
    )
    arm_angle_ok = bool((arm_cov >= config.ARM_ANGLE_COVERAGE_MIN).all())

    # --- pitch-type label stability ----------------------------------------
    types = con.execute(f"""
        SELECT game_year, pitch_type, COUNT(*) AS pitches {base}
        GROUP BY 1, 2 ORDER BY 1, 3 DESC
    """).df()
    totals = types.groupby("game_year")["pitches"].transform("sum")
    types["share_pct"] = (100 * types["pitches"] / totals).round(3)
    stability = types.pivot(index="pitch_type", columns="game_year",
                            values="share_pct").fillna(0.0).round(3)
    stability["max_abs_yoy_change"] = stability.diff(axis=1).abs().max(axis=1).round(3)
    stability = stability.reset_index()
    print("\n=== pitch_type share (%) by season ===")
    print(stability.to_string(index=False))

    sweeper_retro = taxonomy.sweeper_labels_are_retroactive(stability)

    # --- outputs ------------------------------------------------------------
    D.save_result(per_year, "s0_rows_per_season")
    D.save_result(nulls_long, "s0_null_rates")
    D.save_result(stability, "s4_taxonomy_stability")

    manifest = {
        "seasons": per_year.to_dict(orient="records"),
        "total_pitches": int(per_year["pitches"].sum()),
        "arm_angle_coverage_by_year": {int(k): round(float(v), 4)
                                       for k, v in arm_cov.items()},
        "arm_angle_in_feature_vector": arm_angle_ok,
        "sweeper_labels_retroactive": sweeper_retro,
        "shape_features": config.SHAPE_FEATURES + (["arm_angle"] if arm_angle_ok else []),
    }
    (config.RESULTS_DIR / "data_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str)
    )
    D.write_meta("s0_validate", {
        "arm_angle_in_feature_vector": arm_angle_ok,
        "sweeper_labels_retroactive": sweeper_retro,
        "total_pitches": int(per_year["pitches"].sum()),
    })

    print(f"\narm_angle in feature vector: {arm_angle_ok}")
    print(f"sweeper (ST) labels retroactive to {min(config.YEARS)}: {sweeper_retro}")
    con.close()


if __name__ == "__main__":
    main()
