"""S4 - Pitch-type ecology: what is being thrown, and what is it worth?

Usage share and effectiveness per family per season. Effectiveness is also
expressed relative to that season's all-pitch average, which absorbs run
environment drift (ball construction, the 2023 rule changes) so that a pitch
type's trajectory is not confounded with the league's.

The output that matters for the hypothesis is the quadrant scatter: pitch types
whose usage has fallen while their value held up are candidate neglected
niches, examined properly in S6.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import outcomes as oc
from analysis.lib import plotting as P
from analysis.lib import stats as S


def ecology_table(years: list[int]) -> pd.DataFrame:
    frames = []
    for year in years:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=[
            "family", "pitch_type", "game_year", "description", "type", "zone",
            "is_whiff", "is_swing", "is_called_strike", "is_csw", "is_bip",
            "in_zone", "delta_run_exp", "estimated_woba_using_speedangle",
        ])
        fam = oc.aggregate_outcomes(d, ["game_year", "family"])
        fam["usage_share"] = 100 * fam["pitches"] / fam["pitches"].sum()

        # league-wide baseline for the same season
        league = oc.aggregate_outcomes(d.assign(_all="all"), ["game_year", "_all"])
        for col in oc.OUTCOME_COLUMNS:
            base = float(league[col].iloc[0])
            fam[f"{col}_rel"] = fam[col] - base
            fam[f"league_{col}"] = base
        frames.append(fam)
        del d
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fine_type_table(years: list[int]) -> pd.DataFrame:
    """Usage by Savant's fine-grained pitch_type, for the taxonomy discussion."""
    frames = []
    for year in years:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=[
            "pitch_type", "game_year", "description", "type", "zone",
            "is_whiff", "is_swing", "is_called_strike", "is_csw", "is_bip",
            "in_zone", "delta_run_exp", "estimated_woba_using_speedangle",
        ])
        t = oc.aggregate_outcomes(d, ["game_year", "pitch_type"])
        t["usage_share"] = 100 * t["pitches"] / t["pitches"].sum()
        frames.append(t)
        del d
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def usage_value_quadrant(eco: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Change in usage vs change in relative value, first season to last."""
    a = eco[eco["game_year"] == years[0]].set_index("family")
    b = eco[eco["game_year"] == years[-1]].set_index("family")
    common = a.index.intersection(b.index)
    return pd.DataFrame({
        "family": common,
        "usage_share_start": a.loc[common, "usage_share"].to_numpy(),
        "usage_share_end": b.loc[common, "usage_share"].to_numpy(),
        "usage_change_pp": (b.loc[common, "usage_share"]
                            - a.loc[common, "usage_share"]).to_numpy(),
        "rv100_rel_start": a.loc[common, "rv100_rel"].to_numpy(),
        "rv100_rel_end": b.loc[common, "rv100_rel"].to_numpy(),
        "rv100_rel_change": (b.loc[common, "rv100_rel"]
                             - a.loc[common, "rv100_rel"]).to_numpy(),
        "pitches_end": b.loc[common, "pitches"].to_numpy(),
    }).sort_values("usage_change_pp")


def figure_ecology(eco: pd.DataFrame, quad: pd.DataFrame, years: list[int]) -> None:
    """fig08 - usage shares over time and the usage-vs-value quadrant."""
    fams = [f for f in config.FAMILY_ORDER if f in set(eco["family"])]
    fig, axes = P.facet_grid(3, ncols=3, width=3.9, height=3.1)

    ax = axes[0]
    for fam in fams:
        s = eco[eco["family"] == fam].sort_values("game_year")
        ax.plot(s["game_year"], s["usage_share"], color=P.FAMILY_COLOR[fam],
                marker="o", markersize=4, markeredgecolor=P.SURFACE,
                markeredgewidth=0.8)
        last = s.iloc[-1]
        P.direct_label(ax, last["game_year"], last["usage_share"],
                       config.FAMILY_LABELS[fam], P.FAMILY_COLOR[fam], dx=0.12)
    P.style_axis(ax, title="Pitch usage share", ylabel="% of all pitches")
    P.year_axis(ax, years)
    ax.set_xlim(min(years) - 0.3, max(years) + 1.6)

    ax = axes[1]
    for fam in fams:
        s = eco[eco["family"] == fam].sort_values("game_year")
        ax.plot(s["game_year"], s["rv100_rel"], color=P.FAMILY_COLOR[fam],
                marker="o", markersize=4, markeredgecolor=P.SURFACE,
                markeredgewidth=0.8)
        last = s.iloc[-1]
        P.direct_label(ax, last["game_year"], last["rv100_rel"],
                       config.FAMILY_LABELS[fam], P.FAMILY_COLOR[fam], dx=0.12)
    P.zero_line(ax)
    P.style_axis(ax, title="Value relative to the league average",
                 ylabel="Run value/100 above all-pitch mean")
    P.year_axis(ax, years)
    ax.set_xlim(min(years) - 0.3, max(years) + 1.6)

    ax = axes[2]
    if not quad.empty:
        for _, r in quad.iterrows():
            color = P.FAMILY_COLOR.get(r["family"], P.SERIES[0])
            ax.scatter(r["usage_change_pp"], r["rv100_rel_end"], s=90,
                       color=color, edgecolor=P.SURFACE, linewidth=1.4, zorder=3)
            ax.annotate(config.FAMILY_LABELS.get(r["family"], r["family"]),
                        (r["usage_change_pp"], r["rv100_rel_end"]),
                        textcoords="offset points", xytext=(0, 10),
                        ha="center", fontsize=8, color=P.INK_SECONDARY)
    P.zero_line(ax)
    P.zero_line(ax, horizontal=False)
    P.style_axis(ax, title="Abandoned but still effective?",
                 xlabel=f"Change in usage share, {years[0]}→{years[-1]} (pp)",
                 ylabel=f"Relative run value/100, {years[-1]}")
    ax.grid(axis="x", visible=True)

    P.suptitle(fig, "The pitch ecosystem",
               "Upper-left of the third panel = thrown less often than before "
               "while still out-performing the league average")
    P.finish(fig)
    P.save(fig, "fig08_ecology")


def main() -> None:
    arsenal = pd.read_parquet(D.arsenal_path())
    years = sorted(arsenal["game_year"].unique())

    eco = ecology_table(years)
    D.save_result(eco, "s4_family_ecology")

    fine = fine_type_table(years)
    D.save_result(fine, "s4_fine_type_ecology")

    quad = usage_value_quadrant(eco, years)
    D.save_result(quad, "s4_usage_value_quadrant")

    print("=== usage share and relative value by family ===")
    show = eco[["game_year", "family", "usage_share", "rv100", "rv100_rel",
                "csw_pct", "whiff_pct", "xwobacon"]].round(3)
    print(show.to_string(index=False))
    if not quad.empty:
        print(f"\n=== usage vs value, {years[0]} → {years[-1]} ===")
        print(quad.round(3).to_string(index=False))

    figure_ecology(eco, quad, years)
    D.write_meta("s4_ecology", {"years": years})


if __name__ == "__main__":
    main()
