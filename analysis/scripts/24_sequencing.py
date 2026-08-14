"""S9 - Sequencing and count: the missing variables.

The earlier studies used count only as a control and ignored pitch-to-pitch
sequencing entirely. Both matter to the homogeneity question in their own
right:

* **Sequencing.** If individual pitches converge on templates, the contrast
  *between consecutive pitches* becomes a pitcher's remaining degree of
  freedom. Within each at-bat, every pitch after the first gets a shape gap
  from its predecessor (velocity, IVB, horizontal break, standardized on
  league scale), plus a flag for exact shape-cell repetition. The whiff model
  mirrors S7: batter fixed effects by demeaning, count-state and family
  dummies, location and current-shape controls, batter-clustered SEs. Shape
  controls on the *current* pitch matter -- without them the gap coefficient
  would just rediscover that breaking balls follow fastballs.

* **Count.** Two questions. Does the outlier advantage from S5 concentrate in
  particular count states? And do pitchers already deploy their unusual
  pitches as putaway weapons (usage by count)?
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import plotting as P

COLS = ["game_pk", "game_year", "at_bat_number", "pitch_number", "pitcher",
        "batter", "family", "release_speed", "ivb", "hb_arm", "plate_x",
        "plate_z", "balls", "strikes", "stand", "p_throws", "is_whiff",
        "is_swing", "is_csw", "cell_id", "delta_run_exp"]


def count_bucket(balls: pd.Series, strikes: pd.Series) -> pd.Series:
    out = pd.Series("even", index=balls.index)
    out[strikes == 2] = "two_strike"
    out[(strikes > balls) & (strikes < 2)] = "pitcher_ahead"
    out[balls > strikes] = "batter_ahead"
    return out


def load_with_sequence() -> pd.DataFrame:
    frames = []
    for year in config.YEARS:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=[c for c in COLS if c != "game_year"])
        d["game_year"] = year
        d = d.sort_values(["game_pk", "at_bat_number", "pitch_number"])
        grp = d.groupby(["game_pk", "at_bat_number"], sort=False)
        for col in ["release_speed", "ivb", "hb_arm", "family", "cell_id",
                    "pitcher"]:
            d[f"prev_{col}"] = grp[col].shift(1)
        # a mid-at-bat pitching change breaks the sequence
        d = d[d["prev_pitcher"].isna() | (d["prev_pitcher"] == d["pitcher"])]

        # league-scale standardization of the consecutive-pitch gap
        scales = {c: d[c].std() for c in ["release_speed", "ivb", "hb_arm"]}
        gap2 = np.zeros(len(d))
        for c, s in scales.items():
            gap2 = gap2 + (((d[c] - d[f"prev_{c}"]) / s) ** 2).fillna(np.nan)
        d["seq_gap"] = np.sqrt(gap2)
        d["same_cell"] = (d["cell_id"] == d["prev_cell_id"]).astype(float)
        d["same_family"] = (d["family"] == d["prev_family"]).astype(float)
        d["has_prev"] = d["prev_release_speed"].notna()
        frames.append(d.drop(columns=[f"prev_{c}" for c in
                                      ["release_speed", "ivb", "hb_arm",
                                       "family", "cell_id", "pitcher"]]))
    out = pd.concat(frames, ignore_index=True)
    out["count_state"] = out["balls"].astype(str) + "-" + out["strikes"].astype(str)
    out["bucket"] = count_bucket(out["balls"], out["strikes"])
    out["platoon"] = (out["stand"] != out["p_throws"]).astype(int)
    out["loc_dist"] = np.hypot(out["plate_x"].fillna(0),
                               out["plate_z"].fillna(2.5) - 2.5)
    return out


def within_batter_lpm(sub: pd.DataFrame, outcome: str,
                      focal: list[str]) -> dict:
    """Same identification as S7: batter FE by demeaning, clustered SEs."""
    controls = ["loc_dist", "platoon", "release_speed", "ivb", "hb_arm"]
    cols = focal + controls
    sub = sub.dropna(subset=cols + [outcome, "batter"]).copy()
    if len(sub) < 5000:
        return {}
    dummies = pd.get_dummies(sub[["count_state", "family"]], drop_first=True,
                             dtype=float)
    X = pd.concat([sub[cols].astype(float), dummies], axis=1)
    y = sub[outcome].astype(float)
    g = sub["batter"]
    X = X - X.groupby(g.to_numpy()).transform("mean")
    y = y - y.groupby(g.to_numpy()).transform("mean")
    X = sm.add_constant(X, has_constant="add")
    m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": g})
    out = {"outcome": outcome, "n": int(len(sub)),
           "n_batters": int(g.nunique())}
    for f in focal:
        out[f"{f}_coef"] = float(m.params[f])
        out[f"{f}_se"] = float(m.bse[f])
        out[f"{f}_p"] = float(m.pvalues[f])
    return out


def sequencing_models(d: pd.DataFrame) -> pd.DataFrame:
    seq = d[d["has_prev"]]
    rows = []
    for outcome, frame in (("is_whiff", seq[seq["is_swing"] == 1]),
                           ("is_csw", seq)):
        r = within_batter_lpm(frame, outcome, ["seq_gap", "same_cell"])
        if r:
            rows.append(r)
    return pd.DataFrame(rows)


def gap_bins(d: pd.DataFrame) -> pd.DataFrame:
    seq = d[d["has_prev"] & (d["is_swing"] == 1)].copy()
    edges = [0, 0.5, 1.0, 1.5, 2.0, 3.0, np.inf]
    labels = ["0-0.5", "0.5-1", "1-1.5", "1.5-2", "2-3", "3+"]
    seq["gap_bin"] = pd.cut(seq["seq_gap"], edges, labels=labels)
    g = (seq.groupby("gap_bin", observed=True)
         .agg(n=("is_whiff", "size"), whiff_pct=("is_whiff", "mean"))
         .reset_index())
    g["whiff_pct"] = (100 * g["whiff_pct"]).round(2)
    return g


def uniqueness_by_count(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Does the outlier advantage depend on the count?"""
    scored = pd.read_parquet(config.PARQUET_DIR / "arsenal_scored.parquet",
                             columns=["pitcher", "family", "game_year",
                                      "uniq_pct", "uniq_decile"])
    m = d.merge(scored, on=["pitcher", "family", "game_year"], how="inner")

    rows = []
    for bucket, g in m.groupby("bucket"):
        r = within_batter_lpm(g[g["is_swing"] == 1], "is_whiff", ["uniq_pct"])
        if r:
            r["bucket"] = bucket
            rows.append(r)
    per_bucket = pd.DataFrame(rows)

    # do pitchers already save their strangest pitch for two strikes?
    m["is_outlier_pitch"] = (m["uniq_decile"] >= 9).astype(float)
    m["is_typical_pitch"] = (m["uniq_decile"] <= 2).astype(float)
    usage = (m.groupby("bucket")[["is_outlier_pitch", "is_typical_pitch"]]
             .mean().mul(100).round(2).reset_index())
    return per_bucket, usage


def figure(bins: pd.DataFrame, per_bucket: pd.DataFrame) -> None:
    fig, axes = P.facet_grid(2, ncols=2, width=4.6, height=3.4)

    ax = axes[0]
    ax.plot(range(len(bins)), bins["whiff_pct"], marker="o",
            color=P.SERIES[0], lw=1.8)
    ax.set_xticks(range(len(bins)))
    ax.set_xticklabels(bins["gap_bin"], fontsize=8)
    P.style_axis(ax, title="Whiff rate by contrast with the previous pitch",
                 xlabel="Standardized shape gap from previous pitch",
                 ylabel="Whiff% per swing (raw)")

    ax = axes[1]
    order = ["batter_ahead", "even", "pitcher_ahead", "two_strike"]
    pb = per_bucket.set_index("bucket").reindex(order).dropna(how="all")
    coefs = pb["uniq_pct_coef"]
    errs = 1.96 * pb["uniq_pct_se"]
    ax.bar(range(len(pb)), coefs, yerr=errs, capsize=3,
           color=[P.POS if c > 0 else P.NEG for c in coefs], width=0.62)
    ax.set_xticks(range(len(pb)))
    ax.set_xticklabels([b.replace("_", " ") for b in pb.index], fontsize=8)
    P.zero_line(ax)
    P.style_axis(ax, title="Outlier advantage by count state",
                 ylabel="Whiff effect of uniqueness (LPM coef)")

    P.suptitle(fig, "Sequencing and count",
               "Left: raw bins. Right: within-batter estimates with count, "
               "family, location and shape controls")
    P.finish(fig)
    P.save(fig, "fig16_sequencing")


def main() -> None:
    d = load_with_sequence()
    n_seq = int(d["has_prev"].sum())
    print(f"pitches with a previous pitch in the same at-bat: {n_seq:,}")

    models = sequencing_models(d)
    D.save_result(models, "s9_sequencing_models")
    print("\n=== within-batter effect of consecutive-pitch contrast ===")
    print(models.round(5).to_string(index=False))

    bins = gap_bins(d)
    D.save_result(bins, "s9_gap_bins")
    print("\n=== raw whiff rate by shape gap ===")
    print(bins.to_string(index=False))

    per_bucket, usage = uniqueness_by_count(d)
    D.save_result(per_bucket, "s9_uniqueness_by_count")
    D.save_result(usage, "s9_outlier_usage_by_count")
    print("\n=== uniqueness whiff effect by count state ===")
    print(per_bucket.round(5).to_string(index=False))
    print("\n=== where outlier vs typical pitches get thrown (% of pitches) ===")
    print(usage.to_string(index=False))

    figure(bins, per_bucket)
    D.write_meta("s9_sequencing", {"n_sequenced": n_seq})


if __name__ == "__main__":
    main()
