"""S10 - Out-of-sample check: does the 2026 season behave as predicted?

The five-season report made directional claims. This script scores them against
a season that was not available when they were made, which is a genuine
out-of-sample test rather than a refit.

Two rules keep the comparison honest:

* **Date matching.** The current season is incomplete, so every season in this
  run is truncated at the same calendar day (SEASON_CUTOFF_MD). A raw
  comparison of a partial season against full ones confounds "what changed"
  with "August is not October" -- offspeed usage, velocity and roster
  composition all drift late in a season.
* **Direction, not magnitude.** Each claim is scored on whether the new season
  continues the direction the report predicted, since a two-thirds season
  carries wider error bars than the ones behind the original estimates.

Run after the tagged pipeline, e.g.:

    ANALYSIS_TAG=md2026 SEASON_CUTOFF_MD=08-13 \\
    ANALYSIS_YEARS=2021,2022,2023,2024,2025,2026 \\
    python analysis/scripts/25_season_check.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import plotting as P


def read(name: str) -> pd.DataFrame:
    p = config.RESULTS_DIR / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def verdict(continues: bool | None) -> str:
    if continues is None:
        return "no data"
    return "holds" if continues else "breaks"


def check_convergence(rows: list) -> None:
    d = read("s3_directional_convergence")
    if d.empty:
        return
    new = d[d["year_pair"].str.endswith(str(config.FINAL_YEAR))]
    yoy = new[new["series"] == "year_over_year"]
    null = new[new["series"] == "within_year_null"]
    if yoy.empty:
        return
    frac = float(yoy["frac_toward_centre"].iloc[0])
    base = float(null["frac_toward_centre"].iloc[0]) if not null.empty else np.nan
    prior = d[(d["series"] == "year_over_year")
              & ~d["year_pair"].str.endswith(str(config.FINAL_YEAR))]
    rows.append({
        "claim": "Pitchers keep drifting toward the league centre",
        "prior_seasons": f"{100 * prior['frac_toward_centre'].mean():.1f}% inward",
        "new_season": f"{100 * frac:.1f}% inward (null {100 * base:.1f}%)",
        "verdict": verdict(frac > base + 0.03),
    })


def check_newcomers(rows: list) -> None:
    d = read("s3_newcomer_periphery")
    if d.empty:
        return
    new = d[d["game_year"] == config.FINAL_YEAR]
    prior = d[d["game_year"] < config.FINAL_YEAR]
    if new.empty:
        return
    rows.append({
        "claim": "Arriving pitchers are more typical than incumbents",
        "prior_seasons": f"{prior['pct_further'].median():+.1f}% vs established",
        "new_season": f"{new['pct_further'].median():+.1f}% vs established",
        "verdict": verdict(float(new["pct_further"].median()) < 0),
    })


def check_scarcity(rows: list) -> None:
    d = read("s6_scarcity_regression")
    if d.empty:
        return
    x = d[d["outcome"] == "xwobacon"]
    if x.empty:
        return
    coef, p = float(x["scarcity_coef"].iloc[0]), float(x["p"].iloc[0])
    rows.append({
        "claim": "Crowding a shape degrades it (xwOBAcon)",
        "prior_seasons": "+0.0106 per doubling, p=0.0011",
        "new_season": f"{coef:+.4f} per doubling, p={p:.4g}",
        "verdict": verdict(coef > 0 and p < 0.05),
    })


def check_familiarity(rows: list) -> None:
    d = read("s7_familiarity_models")
    if d.empty:
        return
    m = d[(d["outcome"] == "is_whiff") & (d["model"] == "main")]
    if m.empty:
        return
    pp, p = float(m["pp_per_doubling"].iloc[0]), float(m["exposure_p"].iloc[0])
    rows.append({
        "claim": "Recent exposure blunts a pitch",
        "prior_seasons": "-0.42pp whiff per doubling",
        "new_season": f"{pp:+.2f}pp per doubling, p={p:.3g}",
        "verdict": verdict(pp < 0 and p < 0.05),
    })


def check_splitters(rows: list) -> None:
    d = read("s8_splitter_by_year")
    if d.empty or len(d) < 3:
        return
    new = d[d["game_year"] == config.FINAL_YEAR]
    if new.empty:
        return
    first, last = d.iloc[0], new.iloc[0]
    rows.append({
        "claim": "Splitter boom continues to draw practitioners",
        "prior_seasons": f"{int(first['pitchers'])} pitchers in {int(first['game_year'])}",
        "new_season": f"{int(last['pitchers'])} pitchers",
        "verdict": verdict(int(last["pitchers"]) >= int(d.iloc[-2]["pitchers"])),
    })
    rows.append({
        "claim": "Splitter effectiveness erodes as it spreads",
        "prior_seasons": f"whiff {first['whiff_pct']:.1f}% -> "
                         f"{d.iloc[-2]['whiff_pct']:.1f}%",
        "new_season": f"whiff {last['whiff_pct']:.1f}%, RV/100 {last['rv100']:+.2f}",
        "verdict": verdict(float(last["whiff_pct"]) <= float(first["whiff_pct"])),
    })


def check_deathball(rows: list) -> None:
    d = read("s8_deathball_contrast")
    if d.empty:
        return
    new = d[d["game_year"] == config.FINAL_YEAR]
    prior = d[d["game_year"] < config.FINAL_YEAR]
    if new.empty or prior.empty:
        return
    peak = prior.loc[prior["whiff_edge_pp"].idxmax()]
    last_prior = prior.sort_values("game_year").iloc[-1]
    now = float(new["whiff_edge_pp"].iloc[0])
    rows.append({
        "claim": "Deathball edge erodes as adoption spreads",
        "prior_seasons": f"peak +{peak['whiff_edge_pp']:.1f}pp in "
                         f"{int(peak['game_year'])}, then "
                         f"+{last_prior['whiff_edge_pp']:.1f}pp",
        "new_season": f"+{now:.1f}pp, {int(new['db_pitchers'].iloc[0])} pitchers",
        # continuing the decline means falling again, not merely sitting
        # below a peak set three seasons ago
        "verdict": verdict(now <= float(last_prior["whiff_edge_pp"])),
    })


def check_outlier_by_count(rows: list) -> None:
    d = read("s9_uniqueness_by_count")
    if d.empty:
        return
    pos = (d["uniq_pct_coef"] > 0) & (d["uniq_pct_p"] < 0.05)
    rows.append({
        "claim": "Outlier advantage holds across count states",
        "prior_seasons": "+1.8 to +3.0pp, all 4 counts",
        "new_season": f"{int(pos.sum())}/{len(d)} counts positive and significant",
        "verdict": verdict(bool(pos.all())),
    })


def check_ecology(rows: list) -> None:
    d = read("s4_family_ecology")
    if d.empty:
        return
    piv = d.pivot(index="game_year", columns="family", values="usage_share")
    if config.FINAL_YEAR not in piv.index:
        return
    prev, new = piv.loc[config.YEARS[-2]], piv.loc[config.FINAL_YEAR]
    for fam, label, direction in (("FF", "Four-seam usage keeps falling", -1),
                                  ("SLV", "Slider/sweeper usage keeps rising", 1),
                                  ("FS", "Splitter usage keeps rising", 1)):
        if fam not in piv.columns:
            continue
        change = new[fam] - prev[fam]
        rows.append({
            "claim": label,
            "prior_seasons": f"{piv[fam].iloc[0]:.1f}% -> {prev[fam]:.1f}%",
            "new_season": f"{new[fam]:.1f}% ({change:+.2f}pp)",
            "verdict": verdict(change * direction > 0),
        })


def figure(scorecard: pd.DataFrame) -> None:
    eco = read("s4_family_ecology")
    split = read("s8_splitter_by_year")
    db = read("s8_deathball_contrast")
    if eco.empty:
        return
    fig, axes = P.facet_grid(3, ncols=3, width=4.1, height=3.3)

    ax = axes[0]
    piv = eco.pivot(index="game_year", columns="family", values="usage_share")
    for fam in ["FF", "SLV", "FS", "SI", "CH"]:
        if fam in piv.columns:
            ax.plot(piv.index, piv[fam], marker="o", lw=1.6,
                    color=P.FAMILY_COLOR.get(fam), label=fam)
    ax.axvline(config.FINAL_YEAR - 0.5, color=P.AXIS, lw=1, ls=":")
    P.style_axis(ax, title="Usage share by family", ylabel="% of pitches")
    P.year_axis(ax, config.YEARS)
    ax.legend(ncol=3, fontsize=7, loc="upper center",
              bbox_to_anchor=(0.5, -0.18), frameon=False)

    ax = axes[1]
    if not split.empty:
        ax.plot(split["game_year"], split["whiff_pct"], marker="o",
                color=P.SERIES[1], lw=1.8)
        ax.axvline(config.FINAL_YEAR - 0.5, color=P.AXIS, lw=1, ls=":")
    P.style_axis(ax, title="Splitter whiff rate", ylabel="Whiff% per swing")
    P.year_axis(ax, config.YEARS)

    ax = axes[2]
    if not db.empty:
        ax.plot(db["game_year"], db["whiff_edge_pp"], marker="o",
                color=P.SERIES[2], lw=1.8)
        ax.axvline(config.FINAL_YEAR - 0.5, color=P.AXIS, lw=1, ls=":")
        P.zero_line(ax)
    P.style_axis(ax, title="Deathball whiff edge over other sliders",
                 ylabel="Percentage points")
    P.year_axis(ax, config.YEARS)

    P.suptitle(fig, f"{config.FINAL_YEAR} against the five-season record",
               "All seasons truncated to the same calendar window; dotted line "
               f"marks the in-progress {config.FINAL_YEAR} season")
    P.finish(fig)
    P.save(fig, "fig17_season_check")


def main() -> None:
    rows: list = []
    for fn in (check_convergence, check_newcomers, check_scarcity,
               check_familiarity, check_ecology, check_splitters,
               check_deathball, check_outlier_by_count):
        try:
            fn(rows)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"  {fn.__name__} failed: {exc}")
    score = pd.DataFrame(rows)
    if score.empty:
        print("no claims could be scored")
        return
    D.save_result(score, "s10_season_scorecard")
    print(f"=== {config.FINAL_YEAR} scorecard "
          f"(cutoff {config.SEASON_CUTOFF_MD}, all seasons matched) ===")
    print(score.to_string(index=False))
    held = int((score["verdict"] == "holds").sum())
    print(f"\nclaims holding: {held} / {len(score)}")
    figure(score)
    D.write_meta("s10_season_check", {
        "final_year": config.FINAL_YEAR,
        "cutoff": config.SEASON_CUTOFF_MD,
        "claims_holding": held, "claims_scored": len(score),
    })


if __name__ == "__main__":
    main()
