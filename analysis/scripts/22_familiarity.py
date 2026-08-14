"""S7 - The familiarity mechanism.

If outlier pitches work because hitters rarely see them, then the same pitch
should play worse against a hitter who has been seeing that shape a lot lately.

For every pitch, exposure = how many pitches of the same shape cell that batter
faced in the preceding 30 days (the pitch itself excluded). Because exposure
varies across batters facing the *same* pitch, and across time for the *same*
batter, batter fixed effects can be included: the coefficient is then identified
from a hitter's own better and worse-prepared moments, not from differences
between hitters.

This is the closest thing in the study to a causal test, and the one place where
shape and scarcity are genuinely separated.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import plotting as P
from analysis.lib import stats as S

warnings.filterwarnings("ignore")


def build_exposure(window_days: int) -> pd.DataFrame:
    """Trailing-window exposure counts per (batter, shape cell, pitch).

    Computed in DuckDB: a RANGE window over game_date counts prior pitches of
    the same cell the batter faced, which is far cheaper than doing it per
    batter in pandas.
    """
    con = D.connect()
    glob = str(config.PARQUET_DIR / "pitches" / "**" / "*.parquet")
    sql = f"""
        WITH p AS (
            SELECT batter, pitcher, family, cell_id, game_year,
                   CAST(game_date AS DATE) AS gd,
                   balls, strikes, stand, p_throws,
                   plate_x, plate_z, release_speed, ivb, hb_arm,
                   is_swing, is_whiff, is_csw
            FROM read_parquet('{glob}', hive_partitioning=1)
            WHERE cell_id IS NOT NULL AND game_date IS NOT NULL
        ),
        daily AS (
            SELECT batter, cell_id, gd, COUNT(*) AS n_day
            FROM p GROUP BY 1, 2, 3
        ),
        rolling AS (
            SELECT batter, cell_id, gd,
                   COALESCE(SUM(n_day) OVER (
                       PARTITION BY batter, cell_id ORDER BY gd
                       RANGE BETWEEN INTERVAL {window_days} DAYS PRECEDING
                                 AND INTERVAL 1 DAY PRECEDING
                   ), 0) AS exposure
            FROM daily
        ),
        batter_season AS (
            SELECT batter, game_year, COUNT(*) AS batter_pitches
            FROM p GROUP BY 1, 2
        )
        SELECT p.*, r.exposure, bs.batter_pitches
        FROM p
        JOIN rolling r
          ON p.batter = r.batter AND p.cell_id = r.cell_id AND p.gd = r.gd
        JOIN batter_season bs
          ON p.batter = bs.batter AND p.game_year = bs.game_year
        WHERE bs.batter_pitches >= {config.MIN_BATTER_TRAILING}
    """
    df = con.execute(sql).df()
    con.close()
    return df


def prepare(df: pd.DataFrame, uniq: pd.DataFrame) -> pd.DataFrame:
    d = df.merge(uniq, on=["pitcher", "family", "game_year"], how="left")
    d["log_exposure"] = np.log1p(d["exposure"])
    d["platoon"] = (d["stand"] != d["p_throws"]).astype(int)
    d["count_state"] = d["balls"].astype(str) + "-" + d["strikes"].astype(str)
    # crude location quality: distance from the middle of the zone
    d["loc_dist"] = np.hypot(d["plate_x"].fillna(0),
                             d["plate_z"].fillna(2.5) - 2.5)
    return d


def within_batter_lpm(d: pd.DataFrame, outcome: str,
                      interact_uniqueness: bool = False) -> dict:
    """Linear probability model with batter fixed effects.

    Fixed effects are applied by within-batter demeaning rather than thousands
    of dummies; standard errors are clustered on batter.
    """
    cols = ["log_exposure", "loc_dist", "platoon", "release_speed", "ivb",
            "hb_arm"]
    if interact_uniqueness:
        cols += ["uniq_pct", "uniq_x_exposure"]
    sub = d.dropna(subset=cols + [outcome, "batter"]).copy()
    if len(sub) < 5000:
        return {}

    # count-state and family dummies stay as explicit controls
    dummies = pd.get_dummies(sub[["count_state", "family"]], drop_first=True,
                             dtype=float)
    X = pd.concat([sub[cols].astype(float), dummies], axis=1)
    y = sub[outcome].astype(float)

    # within transformation on batter
    g = sub["batter"]
    X = X - X.groupby(g.to_numpy()).transform("mean")
    y = y - y.groupby(g.to_numpy()).transform("mean")
    X = sm.add_constant(X, has_constant="add")

    m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": g})
    return {
        "outcome": outcome, "n": int(len(sub)),
        "n_batters": int(g.nunique()),
        "exposure_coef": float(m.params["log_exposure"]),
        "exposure_se": float(m.bse["log_exposure"]),
        "exposure_p": float(m.pvalues["log_exposure"]),
        # effect of a doubling of recent exposure, in percentage points
        "pp_per_doubling": float(100 * np.log(2) * m.params["log_exposure"]),
        "uniq_x_exposure_coef": (float(m.params["uniq_x_exposure"])
                                 if interact_uniqueness else np.nan),
        "uniq_x_exposure_p": (float(m.pvalues["uniq_x_exposure"])
                              if interact_uniqueness else np.nan),
    }


def exposure_bins(d: pd.DataFrame) -> pd.DataFrame:
    """Descriptive: outcome by exposure bin, overall and by uniqueness half."""
    d = d.copy()
    edges = [-1, 0, 2, 5, 10, 20, 40, 80, np.inf]
    labels = ["0", "1-2", "3-5", "6-10", "11-20", "21-40", "41-80", "80+"]
    d["exposure_bin"] = pd.cut(d["exposure"], bins=edges, labels=labels)
    d["uniq_half"] = np.where(d["uniq_pct"] >= 0.5, "more unusual",
                              "more typical")
    rows = []
    for keys, g in d.groupby(["exposure_bin"], observed=True):
        sw = g[g["is_swing"]]
        rows.append({"exposure_bin": str(keys[0]), "split": "all",
                     "pitches": len(g), "swings": len(sw),
                     "whiff_pct": 100 * sw["is_whiff"].mean() if len(sw) else np.nan,
                     "csw_pct": 100 * g["is_csw"].mean()})
    for keys, g in d.groupby(["exposure_bin", "uniq_half"], observed=True):
        sw = g[g["is_swing"]]
        rows.append({"exposure_bin": str(keys[0]), "split": keys[1],
                     "pitches": len(g), "swings": len(sw),
                     "whiff_pct": 100 * sw["is_whiff"].mean() if len(sw) else np.nan,
                     "csw_pct": 100 * g["is_csw"].mean()})
    return pd.DataFrame(rows)


def figure_familiarity(bins: pd.DataFrame, models: pd.DataFrame,
                       window: int) -> None:
    """fig14 - performance against recent exposure."""
    fig, axes = P.facet_grid(3, ncols=3, width=3.8, height=3.0)
    order = ["0", "1-2", "3-5", "6-10", "11-20", "21-40", "41-80", "80+"]

    ax = axes[0]
    g = bins[bins["split"] == "all"].set_index("exposure_bin").reindex(
        [o for o in order if o in set(bins["exposure_bin"])]).dropna(subset=["whiff_pct"])
    ax.plot(range(len(g)), g["whiff_pct"], color=P.SERIES[0], marker="o",
            markersize=6, markeredgecolor=P.SURFACE, markeredgewidth=1.0)
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels(g.index, fontsize=8, rotation=45, ha="right")
    P.style_axis(ax, title="Whiff rate by recent exposure",
                 xlabel=f"Same-shape pitches seen in prior {window} days",
                 ylabel="Whiff% per swing")

    ax = axes[1]
    for i, (label, gg) in enumerate(
            bins[bins["split"] != "all"].groupby("split")):
        gg = gg.set_index("exposure_bin").reindex(
            [o for o in order if o in set(gg["exposure_bin"])]).dropna(subset=["whiff_pct"])
        ax.plot(range(len(gg)), gg["whiff_pct"], color=P.SERIES[i + 1],
                marker="o", markersize=5, markeredgecolor=P.SURFACE,
                markeredgewidth=1.0, label=label)
        ax.set_xticks(range(len(gg)))
        ax.set_xticklabels(gg.index, fontsize=8, rotation=45, ha="right")
    ax.legend(fontsize=8)
    P.style_axis(ax, title="Split by how unusual the pitch is",
                 xlabel=f"Same-shape pitches seen in prior {window} days",
                 ylabel="Whiff% per swing")

    ax = axes[2]
    if not models.empty:
        s = models.dropna(subset=["pp_per_doubling"])
        ypos = np.arange(len(s))[::-1]
        colors = [P.POS if v > 0 else P.NEG for v in s["pp_per_doubling"]]
        ax.barh(ypos, s["pp_per_doubling"], color=colors, height=0.55)
        ax.errorbar(s["pp_per_doubling"], ypos,
                    xerr=100 * np.log(2) * s["exposure_se"], fmt="none",
                    ecolor=P.INK_SECONDARY, elinewidth=1.2)
        ax.set_yticks(ypos)
        ax.set_yticklabels([o.replace("is_", "").replace("_", " ")
                            for o in s["outcome"]], fontsize=8)
        P.zero_line(ax, horizontal=False)
        ax.grid(axis="x", visible=True)
        ax.grid(axis="y", visible=False)
    P.style_axis(ax, title="Within-batter effect of doubling exposure",
                 xlabel="Change in outcome rate (pp)")

    P.suptitle(fig, "Does familiarity blunt a pitch?",
               "Batter fixed effects: identified from each hitter's own "
               "well- and poorly-prepared moments, not differences between hitters")
    P.finish(fig)
    P.save(fig, "fig14_familiarity")


def main() -> None:
    window = config.EXPOSURE_WINDOW_DAYS
    scored_path = config.PARQUET_DIR / "arsenal_scored.parquet"
    if not scored_path.exists():
        raise SystemExit("run 20_outlier_effectiveness.py first (needs uniqueness)")
    uniq = pd.read_parquet(scored_path)[
        ["pitcher", "family", "game_year", "uniq_pct"]]

    d = prepare(build_exposure(window), uniq)
    print(f"exposure rows: {len(d):,}; median exposure "
          f"{d['exposure'].median():.0f} pitches in prior {window} days")

    bins = exposure_bins(d)
    D.save_result(bins, "s7_exposure_bins")

    rows = []
    for outcome in ("is_whiff", "is_csw"):
        sub = d[d["is_swing"]] if outcome == "is_whiff" else d
        r = within_batter_lpm(sub, outcome)
        if r:
            rows.append(r)
    models = pd.DataFrame(rows)

    inter_rows = []
    di = d.dropna(subset=["uniq_pct"]).copy()
    di["uniq_x_exposure"] = di["uniq_pct"] * di["log_exposure"]
    for outcome in ("is_whiff", "is_csw"):
        sub = di[di["is_swing"]] if outcome == "is_whiff" else di
        r = within_batter_lpm(sub, outcome, interact_uniqueness=True)
        if r:
            r["model"] = "with_uniqueness_interaction"
            inter_rows.append(r)

    if not models.empty:
        models["model"] = "main"
        allm = pd.concat([models, pd.DataFrame(inter_rows)], ignore_index=True)
        allm["sig_fdr"] = S.bh_fdr(allm["exposure_p"].to_numpy(), config.FDR_Q)
        D.save_result(allm, "s7_familiarity_models")
        print("\n=== within-batter effect of recent exposure ===")
        print(allm.round(5).to_string(index=False))

    # sensitivity across alternative windows
    sens = []
    for w in config.EXPOSURE_WINDOW_SENSITIVITY:
        dw = prepare(build_exposure(w), uniq)
        r = within_batter_lpm(dw[dw["is_swing"]], "is_whiff")
        if r:
            r["window_days"] = w
            sens.append(r)
        del dw
    if sens:
        sdf = pd.DataFrame(sens)
        D.save_result(sdf, "s7_window_sensitivity")
        print("\n=== window sensitivity (whiff) ===")
        print(sdf[["window_days", "n", "pp_per_doubling", "exposure_p"]]
              .round(5).to_string(index=False))

    figure_familiarity(bins, models, window)
    D.write_meta("s7_familiarity", {
        "window_days": window,
        "sensitivity_windows": config.EXPOSURE_WINDOW_SENSITIVITY,
        "rows": int(len(d)),
    })


if __name__ == "__main__":
    main()
