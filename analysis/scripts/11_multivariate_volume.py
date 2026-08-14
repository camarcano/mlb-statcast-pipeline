"""S2 - Multivariate volume of the pitch-shape space.

Univariate spread can stay flat while the cloud still collapses, if pitchers
trade one characteristic for another along a single axis (throw harder *and*
flatter, together). This study measures the volume and effective dimensionality
of the whole shape cloud per season:

* log-determinant of the covariance -- the log-volume of the ellipsoid
* participation ratio -- how many dimensions the cloud genuinely occupies
* PCs needed for 90% of variance
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


def volume_table(arsenal_z: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    rows = []
    for family, fam_df in arsenal_z.groupby("family"):
        for year, yr in fam_df.groupby("game_year"):
            X = yr[feats].to_numpy(float)
            X = X[np.isfinite(X).all(axis=1)]
            if X.shape[0] < 40:
                continue
            rows.append({
                "family": family, "game_year": int(year), "n_pitchers": X.shape[0],
                "log_det": S.log_det_cov(X),
                "participation_ratio": S.participation_ratio(X),
                "pcs_90": S.pcs_for_variance(X, 0.90),
                "entropy_nats": S.gaussian_entropy(X),
            })
    return pd.DataFrame(rows)


def league_volume_table(arsenal_z: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """Cross-family volume: captures collapse of the arsenal ecosystem itself."""
    rows = []
    for year, yr in arsenal_z.groupby("game_year"):
        X = yr[feats].to_numpy(float)
        X = X[np.isfinite(X).all(axis=1)]
        if X.shape[0] < 60:
            continue
        rows.append({
            "game_year": int(year), "n_arsenal_rows": X.shape[0],
            "log_det": S.log_det_cov(X),
            "participation_ratio": S.participation_ratio(X),
            "pcs_90": S.pcs_for_variance(X, 0.90),
            "entropy_nats": S.gaussian_entropy(X),
        })
    return pd.DataFrame(rows)


def bootstrap_logdet_change(arsenal_z: pd.DataFrame, feats: list[str],
                            base_year: int, final_year: int,
                            reps: int) -> pd.DataFrame:
    """CI on the change in log-volume, resampling pitchers within each season."""
    rng = np.random.default_rng(config.SEED)
    rows = []
    for family, fam_df in arsenal_z.groupby("family"):
        a = fam_df[fam_df["game_year"] == base_year][feats].to_numpy(float)
        b = fam_df[fam_df["game_year"] == final_year][feats].to_numpy(float)
        a, b = a[np.isfinite(a).all(axis=1)], b[np.isfinite(b).all(axis=1)]
        if a.shape[0] < 40 or b.shape[0] < 40:
            continue
        point = S.log_det_cov(b) - S.log_det_cov(a)
        draws = np.empty(reps)
        for i in range(reps):
            sa = a[rng.integers(0, a.shape[0], a.shape[0])]
            sb = b[rng.integers(0, b.shape[0], b.shape[0])]
            draws[i] = S.log_det_cov(sb) - S.log_det_cov(sa)
        draws = draws[np.isfinite(draws)]
        lo, hi = (np.percentile(draws, [2.5, 97.5]) if draws.size > 50
                  else (np.nan, np.nan))
        frac = float(np.mean(draws <= 0)) if point > 0 else float(np.mean(draws >= 0))
        rows.append({
            "family": family, "delta_log_det": point, "lo": lo, "hi": hi,
            "p_boot": min(1.0, 2 * max(frac, 1 / (draws.size + 1))),
            # a log-det change converts to an equivalent per-axis linear scale
            "equiv_linear_pct": 100 * (np.exp(point / len(feats)) - 1),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["sig_fdr"] = S.bh_fdr(df["p_boot"].to_numpy(), config.FDR_Q)
    return df


def figure_volume(vol: pd.DataFrame, league: pd.DataFrame, years: list[int]) -> None:
    """fig04 - log-volume and effective dimensionality trajectories."""
    fams = [f for f in config.FAMILY_ORDER if f in set(vol["family"])]
    fig, axes = P.facet_grid(3, ncols=3, width=3.9, height=3.0)

    ax = axes[0]
    for fam in fams:
        s = vol[vol["family"] == fam].sort_values("game_year")
        base = s[s["game_year"] == years[0]]["log_det"]
        if base.empty or not np.isfinite(base.iloc[0]):
            continue
        ax.plot(s["game_year"], s["log_det"] - base.iloc[0],
                color=P.FAMILY_COLOR[fam], marker="o", markersize=4,
                markeredgecolor=P.SURFACE, markeredgewidth=0.8,
                label=config.FAMILY_LABELS[fam])
    P.zero_line(ax)
    P.style_axis(ax, title="Shape-space log-volume",
                 ylabel=f"Δ log-determinant vs {years[0]}")
    P.year_axis(ax, years)
    ax.legend(ncol=2, fontsize=7.5)

    ax = axes[1]
    for fam in fams:
        s = vol[vol["family"] == fam].sort_values("game_year")
        ax.plot(s["game_year"], s["participation_ratio"],
                color=P.FAMILY_COLOR[fam], marker="o", markersize=4,
                markeredgecolor=P.SURFACE, markeredgewidth=0.8)
    P.style_axis(ax, title="Effective dimensionality",
                 ylabel="Participation ratio")
    P.year_axis(ax, years)

    ax = axes[2]
    if not league.empty:
        s = league.sort_values("game_year")
        ax.plot(s["game_year"], s["log_det"], color=P.SERIES[0], marker="o",
                markersize=6, markeredgecolor=P.SURFACE, markeredgewidth=1.0)
        for _, r in s.iterrows():
            ax.annotate(f"{r['log_det']:.2f}", (r["game_year"], r["log_det"]),
                        textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8, color=P.INK_SECONDARY)
    P.style_axis(ax, title="All families pooled",
                 ylabel="log-determinant of covariance")
    P.year_axis(ax, years)

    P.suptitle(fig, "Volume of the pitch-shape space",
               "A falling log-volume means the cloud of distinct pitch shapes "
               "is shrinking, even where single characteristics look stable")
    P.finish(fig)
    P.save(fig, "fig04_shape_volume")


def main() -> None:
    manifest = json.loads((config.RESULTS_DIR / "data_manifest.json").read_text())
    feats = manifest["shape_features"]
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 400

    arsenal = pd.read_parquet(D.arsenal_path())
    years = sorted(arsenal["game_year"].unique())
    scaling = F.load_scaling()
    az = F.apply_scaling(arsenal, feats, scaling, by="family")

    vol = volume_table(az, feats)
    D.save_result(vol, "s2_shape_volume")

    league = league_volume_table(az, feats)
    D.save_result(league, "s2_league_volume")

    delta = bootstrap_logdet_change(az, feats, years[0], years[-1], reps)
    if not delta.empty:
        D.save_result(delta, "s2_logdet_change")
        print("=== change in shape-space log-volume, "
              f"{years[0]} → {years[-1]} ===")
        print(delta.to_string(index=False))

    figure_volume(vol, league, years)
    D.write_meta("s2_volume", {"years": years, "features": feats,
                               "bootstrap_reps": reps})


if __name__ == "__main__":
    main()
