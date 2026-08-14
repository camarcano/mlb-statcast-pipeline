"""S3 - Are individual pitchers converging on each other?

Three angles:

* Crowding: how close is the nearest *other* pitcher's version of the same
  pitch? Falling nearest-neighbour distance means the shape space is filling in
  around each pitcher.
* Arsenal diversity: Shannon entropy of a pitcher's pitch mix, and how many
  distinct pitch families he throws meaningfully.
* Directional convergence: for pitchers present in consecutive seasons, does
  their year-over-year movement point toward the league centre?

The directional test needs care. Measurement noise alone produces apparent
regression to the mean, so the displacement is measured on one half of a
pitcher's pitches and the starting position on the other half (split-half
de-noising), and the result is compared against a within-season null built the
same way.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import features as F
from analysis.lib import plotting as P
from analysis.lib import stats as S


def crowding_table(arsenal_z: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    rows = []
    for (family, year), grp in arsenal_z.groupby(["family", "game_year"]):
        X = grp[feats].to_numpy(float)
        ok = np.isfinite(X).all(axis=1)
        X = X[ok]
        if X.shape[0] < config.NN_K_CONVERGENCE + 10:
            continue
        nn = NearestNeighbors(n_neighbors=config.NN_K_CONVERGENCE + 1).fit(X)
        dist, _ = nn.kneighbors(X)
        rows.append({
            "family": family, "game_year": int(year), "n_pitchers": X.shape[0],
            "mean_nn_dist": float(dist[:, 1].mean()),
            "median_nn_dist": float(np.median(dist[:, 1])),
            f"mean_k{config.NN_K_CONVERGENCE}_dist":
                float(dist[:, 1:].mean()),
        })
    return pd.DataFrame(rows)


def arsenal_diversity(arsenal: pd.DataFrame) -> pd.DataFrame:
    """Per pitcher-year usage entropy and count of meaningfully-used families."""
    rows = []
    elig = arsenal[arsenal["pitcher_year_pitches"] >= config.MIN_PITCHES_PITCHER_YEAR]
    for (pitcher, year), g in elig.groupby(["pitcher", "game_year"]):
        shares = g["usage_share"].to_numpy(float)
        rows.append({
            "pitcher": pitcher, "game_year": int(year),
            "n_families": int((shares >= 0.05).sum()),
            "usage_entropy": S.shannon_entropy(shares),
            "top_pitch_share": float(shares.max()),
            "pitches": int(g["pitcher_year_pitches"].iloc[0]),
        })
    per_pitcher = pd.DataFrame(rows)
    summary = (
        per_pitcher.groupby("game_year")
        .agg(n_pitchers=("pitcher", "size"),
             mean_entropy=("usage_entropy", "mean"),
             median_entropy=("usage_entropy", "median"),
             mean_n_families=("n_families", "mean"),
             mean_top_share=("top_pitch_share", "mean"))
        .reset_index()
    )
    return per_pitcher, summary


def directional_convergence(pitches_dir, feats: list[str],
                            years: list[int]) -> pd.DataFrame:
    """Does a pitcher's year-over-year shape change point at the league centre?

    Split-half construction: odd-numbered pitches fix where a pitcher *was*,
    even-numbered pitches measure where he moved to. Because the two halves
    carry independent noise, shrinkage toward the mean caused by measurement
    error cancels rather than masquerading as convergence.
    """
    halves = {}
    for year in years:
        path = pitches_dir / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=["pitcher", "family", "pitch_number",
                                            "at_bat_number"] + feats)
        d["half"] = ((d["at_bat_number"].fillna(0).astype(int)
                      + d["pitch_number"].fillna(0).astype(int)) % 2)
        g = d.groupby(["pitcher", "family", "half"])
        cent = g[feats].median()
        cent["n"] = g.size()
        halves[year] = cent.reset_index()
        del d

    rows = []
    for y0, y1 in zip(years[:-1], years[1:]):
        if y0 not in halves or y1 not in halves:
            continue
        a, b = halves[y0], halves[y1]
        # league centre from the full season, both halves pooled
        centre = (
            pd.concat([a, b]).groupby("family")[feats].median()
        )
        a0 = a[(a["half"] == 0) & (a["n"] >= config.MIN_PITCHES_DIRECTIONAL / 2)]
        b1 = b[(b["half"] == 1) & (b["n"] >= config.MIN_PITCHES_DIRECTIONAL / 2)]
        a1 = a[(a["half"] == 1) & (a["n"] >= config.MIN_PITCHES_DIRECTIONAL / 2)]

        merged = a0.merge(b1, on=["pitcher", "family"], suffixes=("_a", "_b"))
        null_merge = a0.merge(a1, on=["pitcher", "family"], suffixes=("_a", "_b"))

        for label, m in (("year_over_year", merged), ("within_year_null", null_merge)):
            if m.empty:
                continue
            cos = []
            for fam, g in m.groupby("family"):
                if fam not in centre.index:
                    continue
                c = centre.loc[fam, feats].to_numpy(float)
                start = g[[f + "_a" for f in feats]].to_numpy(float)
                end = g[[f + "_b" for f in feats]].to_numpy(float)
                # scale each axis by league spread so the cosine is not
                # dominated by whichever feature has the biggest raw units
                scale = np.nanstd(start, axis=0)
                scale[scale == 0] = 1.0
                move = (end - start) / scale
                toward = (c - start) / scale
                nm = np.linalg.norm(move, axis=1)
                nt = np.linalg.norm(toward, axis=1)
                ok = (nm > 1e-9) & (nt > 1e-9) & np.isfinite(nm) & np.isfinite(nt)
                if ok.sum() == 0:
                    continue
                cos.extend(((move[ok] * toward[ok]).sum(axis=1)
                            / (nm[ok] * nt[ok])).tolist())
            if cos:
                arr = np.asarray(cos)
                rows.append({
                    "year_pair": f"{y0}->{y1}", "series": label,
                    "n": int(arr.size), "mean_cosine": float(arr.mean()),
                    "median_cosine": float(np.median(arr)),
                    "frac_toward_centre": float((arr > 0).mean()),
                })
    return pd.DataFrame(rows)


def newcomer_periphery(arsenal_z: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """Are arriving pitchers stranger than the ones already here?

    This reconciles the study's two headline results. Incumbents drift toward
    the league centre every season (directional convergence), yet the spread of
    the league as a whole does not shrink. Something must be refilling the
    edges. The natural candidate is turnover: if pitchers appearing for the
    first time sit further from the centre than established ones, the league
    keeps its variety through replacement even while individuals converge.

    Distance is measured in the same standardized shape space, against the
    centre of that season's family, so newcomers and incumbents are judged on
    identical terms.
    """
    d = arsenal_z.dropna(subset=feats).copy()
    first_seen = d.groupby("pitcher")["game_year"].transform("min")
    d["is_newcomer"] = d["game_year"] == first_seen
    years = sorted(d["game_year"].unique())

    rows = []
    for (family, year), g in d.groupby(["family", "game_year"]):
        # the earliest season cannot distinguish debuts from incumbents
        if year == years[0] or len(g) < 40:
            continue
        centre = g[feats].to_numpy(float).mean(axis=0)
        dist = np.linalg.norm(g[feats].to_numpy(float) - centre, axis=1)
        new, old = dist[g["is_newcomer"].to_numpy()], dist[~g["is_newcomer"].to_numpy()]
        if new.size < 10 or old.size < 10:
            continue
        rows.append({
            "family": family, "game_year": int(year),
            "n_newcomers": int(new.size), "n_established": int(old.size),
            "newcomer_dist": float(new.mean()),
            "established_dist": float(old.mean()),
            "pct_further": float(100 * (new.mean() / old.mean() - 1.0)),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # one paired test across family-seasons: are newcomers further out?
    diff = df["newcomer_dist"] - df["established_dist"]
    stat, p = wilcoxon(diff) if len(diff) >= 6 else (np.nan, np.nan)
    df.attrs["paired_p"] = float(p)
    df.attrs["median_pct_further"] = float(df["pct_further"].median())
    df.attrs["frac_further"] = float((diff > 0).mean())
    return df


def figure_convergence(crowd: pd.DataFrame, div_summary: pd.DataFrame,
                       direction: pd.DataFrame, years: list[int]) -> None:
    """fig06 - crowding, arsenal entropy and directional drift."""
    fams = [f for f in config.FAMILY_ORDER if f in set(crowd["family"])]
    fig, axes = P.facet_grid(3, ncols=3, width=3.9, height=3.0)

    ax = axes[0]
    for fam in fams:
        s = crowd[crowd["family"] == fam].sort_values("game_year")
        base = s[s["game_year"] == years[0]]["mean_nn_dist"]
        if base.empty or not np.isfinite(base.iloc[0]) or base.iloc[0] == 0:
            continue
        ax.plot(s["game_year"], 100 * (s["mean_nn_dist"] / base.iloc[0] - 1),
                color=P.FAMILY_COLOR[fam], marker="o", markersize=4,
                markeredgecolor=P.SURFACE, markeredgewidth=0.8,
                label=config.FAMILY_LABELS[fam])
    P.zero_line(ax)
    P.style_axis(ax, title="Crowding of the shape space",
                 ylabel=f"% change in nearest-neighbour distance vs {years[0]}")
    P.year_axis(ax, years)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(ncol=2, fontsize=7.5)

    ax = axes[1]
    if not div_summary.empty:
        s = div_summary.sort_values("game_year")
        ax.plot(s["game_year"], s["mean_entropy"], color=P.SERIES[0], marker="o",
                markersize=6, markeredgecolor=P.SURFACE, markeredgewidth=1.0)
        for _, r in s.iterrows():
            ax.annotate(f"{r['mean_entropy']:.3f}",
                        (r["game_year"], r["mean_entropy"]),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=8, color=P.INK_SECONDARY)
    P.style_axis(ax, title="Arsenal diversity",
                 ylabel="Mean usage entropy (nats)")
    P.year_axis(ax, years)

    ax = axes[2]
    if not direction.empty:
        for i, (label, g) in enumerate(direction.groupby("series")):
            g = g.sort_values("year_pair")
            ax.plot(range(len(g)), g["mean_cosine"], color=P.SERIES[i],
                    marker="o", markersize=6, markeredgecolor=P.SURFACE,
                    markeredgewidth=1.0,
                    label=label.replace("_", " "))
            ax.set_xticks(range(len(g)))
            ax.set_xticklabels([p.replace("->", "→")[2:].replace("20", "")
                                for p in g["year_pair"]], fontsize=8)
        ax.legend(fontsize=8)
    P.zero_line(ax)
    P.style_axis(ax, title="Movement toward the league centre",
                 ylabel="Mean cosine (positive = converging)")

    P.suptitle(fig, "Are pitchers converging on each other?",
               "Nearest-neighbour distance measures how crowded each pitcher's "
               "corner of the shape space has become")
    P.finish(fig)
    P.save(fig, "fig06_convergence")


def main() -> None:
    manifest = json.loads((config.RESULTS_DIR / "data_manifest.json").read_text())
    feats = manifest["shape_features"]

    arsenal = pd.read_parquet(D.arsenal_path())
    years = sorted(arsenal["game_year"].unique())
    scaling = F.load_scaling()
    az = F.apply_scaling(arsenal, feats, scaling, by="family")

    crowd = crowding_table(az, feats)
    D.save_result(crowd, "s3_crowding")

    per_pitcher, div_summary = arsenal_diversity(arsenal)
    D.save_result(div_summary, "s3_arsenal_diversity")

    newcomers = newcomer_periphery(az, feats)
    if not newcomers.empty:
        D.save_result(newcomers, "s3_newcomer_periphery")
        print("\n=== do arriving pitchers sit further from the centre? ===")
        print(newcomers.groupby("game_year")[
            ["newcomer_dist", "established_dist", "pct_further"]].mean().round(3).to_string())
        print(f"  family-seasons where newcomers are further out: "
              f"{newcomers.attrs['frac_further']:.0%}"
              f"   median gap: {newcomers.attrs['median_pct_further']:+.1f}%"
              f"   paired p = {newcomers.attrs['paired_p']:.4g}")

    direction = directional_convergence(config.PARQUET_DIR / "pitches", feats, years)
    if not direction.empty:
        D.save_result(direction, "s3_directional_convergence")
        print("=== directional convergence (cosine toward league centre) ===")
        print(direction.to_string(index=False))

    print("\n=== arsenal diversity by season ===")
    print(div_summary.to_string(index=False))

    figure_convergence(crowd, div_summary, direction, years)
    D.write_meta("s3_convergence", {
        "years": years, "features": feats,
        "min_pitches_directional": config.MIN_PITCHES_DIRECTIONAL,
        "pitcher_years": int(len(per_pitcher)),
    })


if __name__ == "__main__":
    main()
