"""S1 - Univariate dispersion trends, 2021 to 2025.

The direct test of the homogenisation hypothesis: is the league-wide spread of
each pitch characteristic shrinking? Computed on arsenal rows (one row per
pitcher-family-year) so that a reliever throwing 300 sliders and a starter
throwing 3,000 count once each -- the question is whether *pitchers* are
converging, not whether pitch usage is concentrating.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import features as F
from analysis.lib import plotting as P
from analysis.lib import stats as S


def dispersion_table(arsenal: pd.DataFrame, feats: list[str],
                     reps: int) -> pd.DataFrame:
    rows = []
    for family, fam_df in arsenal.groupby("family"):
        for feat in feats:
            for year, yr_df in fam_df.groupby("game_year"):
                sub = yr_df[["pitcher", feat]].dropna()
                if len(sub) < 20:
                    continue
                rec = {"family": family, "feature": feat, "game_year": int(year),
                       "n_pitchers": len(sub), "median": float(sub[feat].median())}
                for stat_name, func in S.DISPERSION_FUNCS.items():
                    pt, lo, hi = S.cluster_bootstrap_ci(
                        sub, feat, func, reps=reps, seed=config.SEED
                    )
                    rec[stat_name] = pt
                    rec[f"{stat_name}_lo"] = lo
                    rec[f"{stat_name}_hi"] = hi
                rows.append(rec)
    return pd.DataFrame(rows)


def contrast_table(arsenal: pd.DataFrame, feats: list[str], reps: int,
                   base_year: int, final_year: int) -> pd.DataFrame:
    rows = []
    for family, fam_df in arsenal.groupby("family"):
        a = fam_df[fam_df["game_year"] == base_year]
        b = fam_df[fam_df["game_year"] == final_year]
        if len(a) < 20 or len(b) < 20:
            continue
        for feat in feats:
            da = a[["pitcher", feat]].dropna()
            db = b[["pitcher", feat]].dropna()
            if len(da) < 20 or len(db) < 20:
                continue
            for stat_name in ("sd", "iqr"):
                res = S.cluster_bootstrap_contrast(
                    da, db, feat, S.DISPERSION_FUNCS[stat_name],
                    reps=reps, seed=config.SEED, relative=True,
                )
                # Levene / Brown-Forsythe across all seasons
                groups = [g[feat].dropna().to_numpy()
                          for _, g in fam_df.groupby("game_year")]
                bf_stat, bf_p = S.brown_forsythe(groups)
                # robust monotone trend in the per-year dispersion series
                per_year = (
                    fam_df.groupby("game_year")[feat]
                    .apply(S.DISPERSION_FUNCS[stat_name]).dropna()
                )
                ts = S.theil_sen_slope(per_year.index.to_numpy(),
                                        per_year.to_numpy())
                rows.append({
                    "family": family, "feature": feat, "stat": stat_name,
                    "pct_change": 100 * res["point"],
                    "lo_pct": 100 * res["lo"], "hi_pct": 100 * res["hi"],
                    "p_boot": res["p_two_sided"],
                    "brown_forsythe_stat": bf_stat, "brown_forsythe_p": bf_p,
                    "theil_sen_slope_per_year": ts["slope"],
                    "n_base": len(da), "n_final": len(db),
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["sig_fdr"] = S.bh_fdr(df["p_boot"].to_numpy(), config.FDR_Q)
    return df


def spin_sensitivity(pitches_dir, feats, base_year, final_year) -> pd.DataFrame:
    """Spin dispersion excluding the pre-enforcement portion of 2021.

    Foreign-substance enforcement began 2021-06-21 and cut league spin sharply;
    any 2021-anchored spin comparison must be shown to survive its removal.
    """
    rows = []
    for year in (base_year, final_year):
        path = pitches_dir / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=["pitcher", "family", "game_date",
                                            "release_spin_rate"])
        for label, sub in (
            ("full_season", d),
            ("post_enforcement", d[d["game_date"].astype(str) > config.STICKY_STUFF_DATE]),
        ):
            ars = (sub.groupby(["pitcher", "family"])["release_spin_rate"]
                   .agg(["median", "size"]).reset_index())
            ars = ars[ars["size"] >= config.MIN_PITCHES_ARSENAL]
            for family, g in ars.groupby("family"):
                rows.append({"game_year": year, "window": label, "family": family,
                             "n_pitchers": len(g),
                             "spin_sd": S.sd(g["median"].to_numpy()),
                             "spin_iqr": S.iqr(g["median"].to_numpy())})
    return pd.DataFrame(rows)


def figure_dispersion(disp: pd.DataFrame, feats: list[str], years: list[int]) -> None:
    """fig01 - normalised dispersion trajectories, one panel per feature."""
    fams = [f for f in config.FAMILY_ORDER if f in set(disp["family"])]
    fig, axes = P.facet_grid(len(feats), ncols=4, width=3.2, height=2.5)
    for ax, feat in zip(axes, feats):
        sub = disp[disp["feature"] == feat]
        for fam in fams:
            s = sub[sub["family"] == fam].sort_values("game_year")
            if s.empty or s["sd"].isna().all():
                continue
            base = s[s["game_year"] == years[0]]["sd"]
            if base.empty or not np.isfinite(base.iloc[0]) or base.iloc[0] == 0:
                continue
            y = 100 * (s["sd"] / base.iloc[0] - 1)
            ax.plot(s["game_year"], y, color=P.FAMILY_COLOR[fam], marker="o",
                    markersize=4, markeredgecolor=P.SURFACE, markeredgewidth=0.8)
        P.zero_line(ax)
        P.style_axis(ax, title=config.FEATURE_LABELS.get(feat, feat))
        P.year_axis(ax, years)
        ax.set_ylabel(f"% change in SD vs {years[0]}", fontsize=8)
    handles = [
        __import__("matplotlib").lines.Line2D([], [], color=P.FAMILY_COLOR[f],
                                              marker="o", markersize=4,
                                              label=config.FAMILY_LABELS[f])
        for f in fams
    ]
    fig.legend(handles=handles, loc="lower center", ncol=len(fams),
               bbox_to_anchor=(0.5, -0.02))
    P.suptitle(fig, "Spread of pitch characteristics across pitchers",
               f"Standard deviation of pitcher medians, indexed to {years[0]}; "
               "below zero means pitchers look more alike")
    P.finish(fig, bottom=0.05)
    P.save(fig, "fig01_dispersion_trends")


def figure_contrast(contr: pd.DataFrame, years: list[int]) -> None:
    """fig02 - the headline contrast: change in SD from first to last season."""
    sub = contr[contr["stat"] == "sd"].copy()
    if sub.empty:
        return
    fams = [f for f in config.FAMILY_ORDER if f in set(sub["family"])]
    fig, axes = P.facet_grid(len(fams), ncols=4, width=3.3, height=2.7)
    for ax, fam in zip(axes, fams):
        s = sub[sub["family"] == fam].set_index("feature")
        order = [f for f in config.SHAPE_FEATURES + ["arm_angle"] if f in s.index]
        s = s.loc[order]
        ypos = np.arange(len(s))[::-1]
        colors = [P.NEG if v < 0 else P.POS for v in s["pct_change"]]
        ax.barh(ypos, s["pct_change"], color=colors, height=0.62)
        ax.errorbar(s["pct_change"], ypos,
                    xerr=[s["pct_change"] - s["lo_pct"], s["hi_pct"] - s["pct_change"]],
                    fmt="none", ecolor=P.INK_SECONDARY, elinewidth=1.1)
        ax.set_yticks(ypos)
        ax.set_yticklabels([config.FEATURE_LABELS.get(f, f).split(" (")[0]
                            for f in s.index], fontsize=8)
        P.zero_line(ax, horizontal=False)
        P.style_axis(ax, title=config.FAMILY_LABELS.get(fam, fam))
        ax.grid(axis="x", visible=True)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel(f"% change in SD, {years[0]}→{years[-1]}", fontsize=8)
    P.suptitle(fig, "Change in league-wide spread, first season to last",
               "Bars left of zero = pitchers converged on that characteristic; "
               "whiskers are 95% pitcher-bootstrap intervals")
    P.finish(fig)
    P.save(fig, "fig02_dispersion_contrast")


def main() -> None:
    manifest = json.loads((config.RESULTS_DIR / "data_manifest.json").read_text())
    feats = manifest["shape_features"]
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else config.BOOT_REPS

    arsenal = pd.read_parquet(D.arsenal_path())
    years = sorted(arsenal["game_year"].unique())
    base_year, final_year = years[0], years[-1]

    disp = dispersion_table(arsenal, feats, reps)
    D.save_result(disp, "s1_dispersion_by_year")

    contr = contrast_table(arsenal, feats, reps, base_year, final_year)
    D.save_result(contr, "s1_dispersion_contrast")

    # primary endpoint: one number per family, median across features
    if not contr.empty:
        primary = (
            contr[contr["stat"] == "sd"]
            .groupby("family")["pct_change"].median()
            .rename("median_pct_change_in_sd").reset_index()
            .sort_values("median_pct_change_in_sd")
        )
        D.save_result(primary, "s1_primary_endpoint")
        print("\n=== primary endpoint: median % change in SD across features ===")
        print(primary.to_string(index=False))
        print(f"\nfeatures narrowing (FDR q={config.FDR_Q}): "
              f"{int(((contr['stat']=='sd') & contr['sig_fdr'] & (contr['pct_change']<0)).sum())}"
              f" / {int((contr['stat']=='sd').sum())}")

    spin = spin_sensitivity(config.PARQUET_DIR / "pitches", feats,
                            base_year, final_year)
    if not spin.empty:
        D.save_result(spin, "s1_spin_sticky_sensitivity")

    figure_dispersion(disp, feats, years)
    figure_contrast(contr, years)

    D.write_meta("s1_dispersion", {
        "years": years, "features": feats, "bootstrap_reps": reps,
        "grain": "pitcher-family-year arsenal rows",
    })


if __name__ == "__main__":
    main()
