"""S6 - Scarcity and payoff: are abandoned shape niches more effective?

The decile analysis in S5 cannot separate "unusual shapes are better" from
"unusual shapes are rare *because* they are hard to hit". This study fixes the
shape and varies only its scarcity.

The shape space is cut into velocity x IVB x horizontal-break cells. Each cell
is observed in all five seasons with a different league-wide usage share. A
fixed-effects regression of outcome on log usage share therefore asks: when
this exact shape became rarer, did it get better? Cell fixed effects absorb
everything permanent about the shape; year fixed effects absorb league-wide
drift.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import outcomes as oc
from analysis.lib import plotting as P
from analysis.lib import stats as S


def cell_panel(years: list[int]) -> pd.DataFrame:
    frames = []
    for year in years:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=[
            "cell_id", "family", "game_year", "cell_velo", "cell_ivb", "cell_hb",
            "description", "type", "zone", "is_whiff", "is_swing",
            "is_called_strike", "is_csw", "is_bip", "in_zone",
            "delta_run_exp", "estimated_woba_using_speedangle", "pitcher",
        ])
        keys = ["game_year", "family", "cell_id", "cell_velo", "cell_ivb", "cell_hb"]
        agg = oc.aggregate_outcomes(d, keys)
        agg["usage_share"] = agg["pitches"] / agg["pitches"].sum()
        n_pitchers = (d.groupby(keys, dropna=False)["pitcher"].nunique()
                      .rename("n_pitchers").reset_index())
        agg = agg.merge(n_pitchers, on=keys, how="left")
        # league baseline for the season, so outcomes are relative
        league = oc.aggregate_outcomes(d.assign(_a="a"), ["game_year", "_a"])
        for col in oc.OUTCOME_COLUMNS:
            agg[f"{col}_rel"] = agg[col] - float(league[col].iloc[0])
        frames.append(agg)
        del d
    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if panel.empty:
        return panel
    panel = panel[panel["pitches"] >= config.MIN_CELL_PITCHES].copy()
    # keep only cells observed in every season, so the within-cell comparison
    # is not contaminated by cells entering and leaving the sample
    counts = panel.groupby("cell_id")["game_year"].nunique()
    balanced = counts[counts == len(years)].index
    panel["balanced"] = panel["cell_id"].isin(balanced)
    panel["log_usage"] = np.log(panel["usage_share"])
    return panel


def scarcity_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    """Within-cell effect of scarcity on effectiveness.

    Cell fixed effects are absorbed by weighted within-cell demeaning rather
    than dummy coding: there are thousands of cells, and an explicit design
    matrix would be tens of thousands of rows wide. Year effects stay as
    dummies, and standard errors are clustered on cell.
    """
    rows = []
    bal = panel[panel["balanced"]]
    if bal.empty or bal["game_year"].nunique() < 2:
        return pd.DataFrame()
    bal = bal.copy()
    year_dummies = pd.get_dummies(bal["game_year"].astype(str), prefix="yr",
                                   drop_first=True, dtype=float)
    bal = pd.concat([bal, year_dummies], axis=1)
    year_cols = list(year_dummies.columns)

    for col in ["whiff_pct_rel", "csw_pct_rel", "rv100_rel", "xwobacon_rel"]:
        sub = bal.dropna(subset=[col, "log_usage"])
        if len(sub) < 100 or sub["cell_id"].nunique() < 20:
            continue
        w = sub["pitches"].to_numpy(float)
        cell = sub["cell_id"].to_numpy()
        X = sub[["log_usage"] + year_cols].astype(float)
        y = sub[col].astype(float)

        # weighted demeaning within cell absorbs the cell fixed effects
        wser = pd.Series(w, index=sub.index)
        def _demean(frame):
            num = (frame.mul(wser, axis=0)).groupby(cell).transform("sum")
            den = wser.groupby(cell).transform("sum")
            return frame - num.div(den, axis=0)

        Xd = _demean(X)
        yd = _demean(y.to_frame())[col]
        try:
            m = sm.WLS(yd, sm.add_constant(Xd, has_constant="add"),
                       weights=w).fit(cov_type="cluster",
                                       cov_kwds={"groups": cell})
        except Exception as exc:  # pragma: no cover - defensive
            print(f"  scarcity model failed for {col}: {exc}")
            continue
        base = col.replace("_rel", "")
        rows.append({
            "outcome": base, "n_cell_years": int(len(sub)),
            "n_cells": int(sub["cell_id"].nunique()),
            "scarcity_coef": float(m.params["log_usage"]),
            "se": float(m.bse["log_usage"]),
            "p": float(m.pvalues["log_usage"]),
            # a halving of usage = -0.693 in log units
            "effect_of_halving_usage":
                float(-np.log(2) * m.params["log_usage"]),
            "helps_pitcher_when_rare": bool(
                np.sign(-m.params["log_usage"]) == oc.OUTCOME_SIGN[base]),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["sig_fdr"] = S.bh_fdr(df["p"].to_numpy(), config.FDR_Q)
    return df


def abandoned_niches(panel: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Cells whose usage fell most while their value held up."""
    bal = panel[panel["balanced"]]
    if bal.empty:
        return pd.DataFrame()
    a = bal[bal["game_year"] == years[0]].set_index("cell_id")
    b = bal[bal["game_year"] == years[-1]].set_index("cell_id")
    common = a.index.intersection(b.index)
    if common.empty:
        return pd.DataFrame()
    out = pd.DataFrame({
        "cell_id": common,
        "family": b.loc[common, "family"],
        "velo_lo": b.loc[common, "cell_velo"] * config.CELL_VELO_BIN,
        "ivb_lo": b.loc[common, "cell_ivb"] * config.CELL_IVB_BIN,
        "hb_lo": b.loc[common, "cell_hb"] * config.CELL_HB_BIN,
        "usage_start_pct": 100 * a.loc[common, "usage_share"],
        "usage_end_pct": 100 * b.loc[common, "usage_share"],
        "usage_change_pct_rel": 100 * (b.loc[common, "usage_share"]
                                       / a.loc[common, "usage_share"] - 1),
        "rv100_rel_end": b.loc[common, "rv100_rel"],
        "csw_rel_end": b.loc[common, "csw_pct_rel"],
        "pitches_end": b.loc[common, "pitches"],
    }).reset_index(drop=True)
    out = out[out["rv100_rel_end"] >= 0].sort_values("usage_change_pct_rel")
    return out.head(20).round(3)


def figure_niches(panel: pd.DataFrame, scarcity: pd.DataFrame,
                  years: list[int]) -> None:
    """fig13 - where the shape space emptied out, and what it was worth."""
    fams = ["FF", "SLV", "SI", "CH"]
    fams = [f for f in fams if f in set(panel["family"])]
    n = len(fams) + 1
    fig, axes = P.facet_grid(n, ncols=min(n, 3), width=3.7, height=3.1)

    a_year, b_year = years[0], years[-1]
    for ax, fam in zip(axes, fams):
        sub = panel[(panel["family"] == fam) & panel["balanced"]]
        a = sub[sub["game_year"] == a_year].set_index("cell_id")
        b = sub[sub["game_year"] == b_year].set_index("cell_id")
        common = a.index.intersection(b.index)
        if common.empty:
            continue
        change = 100 * (b.loc[common, "usage_share"]
                        / a.loc[common, "usage_share"] - 1)
        x = b.loc[common, "cell_hb"] * config.CELL_HB_BIN
        y = b.loc[common, "cell_ivb"] * config.CELL_IVB_BIN
        lim = float(np.nanpercentile(np.abs(change), 90)) or 1.0
        sc = ax.scatter(x, y, c=change, cmap="RdBu", vmin=-lim, vmax=lim,
                        s=np.sqrt(b.loc[common, "pitches"]) / 2.5,
                        edgecolor=P.SURFACE, linewidth=0.6)
        P.style_axis(ax, title=config.FAMILY_LABELS.get(fam, fam),
                     xlabel="Horizontal break, arm-side (in)",
                     ylabel="Induced vertical break (in)")
        ax.grid(axis="x", visible=True)
        cb = fig.colorbar(sc, ax=ax, fraction=0.046)
        cb.ax.tick_params(labelsize=7)
        cb.set_label(f"% change in usage\n{a_year}→{b_year}", fontsize=7.5)

    ax = axes[len(fams)]
    if not scarcity.empty:
        order = ["whiff_pct", "csw_pct", "rv100", "xwobacon"]
        s = scarcity.set_index("outcome").reindex(
            [o for o in order if o in set(scarcity["outcome"])])
        ypos = np.arange(len(s))[::-1]
        eff = s["effect_of_halving_usage"]
        colors = [P.POS if (np.sign(v) == oc.OUTCOME_SIGN[o]) else P.NEG
                  for v, o in zip(eff, s.index)]
        ax.barh(ypos, eff, color=colors, height=0.6)
        ax.errorbar(eff, ypos, xerr=np.log(2) * s["se"], fmt="none",
                    ecolor=P.INK_SECONDARY, elinewidth=1.2)
        ax.set_yticks(ypos)
        ax.set_yticklabels([oc.OUTCOME_LABELS[o].split(" (")[0] for o in s.index],
                           fontsize=8)
        P.zero_line(ax, horizontal=False)
        ax.grid(axis="x", visible=True)
        ax.grid(axis="y", visible=False)
    P.style_axis(ax, title="Effect of a shape becoming twice as rare",
                 xlabel="Change in outcome (within-cell)")

    P.suptitle(fig, "Emptied niches in the shape space",
               "Blue cells lost usage. The final panel holds the shape fixed "
               "and varies only how often the league throws it")
    P.finish(fig)
    P.save(fig, "fig13_niches")


def main() -> None:
    arsenal = pd.read_parquet(D.arsenal_path())
    years = sorted(arsenal["game_year"].unique())

    panel = cell_panel(years)
    if panel.empty:
        raise SystemExit("no shape cells met the minimum-pitch threshold")
    D.save_result(
        panel[["game_year", "family", "cell_id", "pitches", "n_pitchers",
               "usage_share", "balanced", "whiff_pct", "csw_pct", "rv100",
               "xwobacon", "rv100_rel", "csw_pct_rel"]].round(5),
        "s6_cell_panel",
    )
    print(f"cells: {panel['cell_id'].nunique():,} "
          f"({panel[panel['balanced']]['cell_id'].nunique():,} present in all "
          f"{len(years)} seasons)")

    scarcity = scarcity_regressions(panel)
    if not scarcity.empty:
        D.save_result(scarcity, "s6_scarcity_regression")
        print("\n=== within-cell effect of scarcity ===")
        print(scarcity.round(5).to_string(index=False))

    aband = abandoned_niches(panel, years)
    if not aband.empty:
        D.save_result(aband, "s6_abandoned_niches")
        print("\n=== most-abandoned cells that still beat league average ===")
        print(aband.head(10).to_string(index=False))

    figure_niches(panel, scarcity, years)
    D.write_meta("s6_niches", {
        "years": years,
        "cell_bins": {"velo": config.CELL_VELO_BIN, "ivb": config.CELL_IVB_BIN,
                       "hb": config.CELL_HB_BIN},
        "min_cell_pitches": config.MIN_CELL_PITCHES,
    })


if __name__ == "__main__":
    main()
