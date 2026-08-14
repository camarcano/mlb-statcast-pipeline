"""S8 - The two live recolonizations: splitters and the deathball.

The main studies treat pitch families symmetrically, which starves the two
most interesting current cases of attention:

* **Splitters** doubled in usage (1.6% -> 3.4%) but were excluded from the
  dispersion endpoint because too few pitchers threw 100 of them in 2021.
  Here the threshold drops to 50 pitches and the pitch gets a full profile:
  who adopted it, what happened to its effectiveness as it spread, and
  whether the widening dispersion (+18.7% at the 100-pitch cut) is real.

* **The deathball** -- practitioner shorthand for a hard gyro slider with
  near-zero horizontal break and a few inches of depth, popularized around
  2024 (Ryne Nelson, Roki Sasaki). Statcast files it under SL, so no family
  analysis can see it. It is exactly what this study predicts should exist:
  a scarce shape cell being deliberately colonized. Operational definition
  here: slider-family pitch, >= 85 mph, |horizontal break| <= 3", IVB <= -2"
  (strict variant: |HB| <= 2", IVB <= -4").
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import plotting as P

MIN_SPLITTER_PITCHES = 50


def load_family(family: str, cols: list[str]) -> pd.DataFrame:
    frames = []
    for year in config.YEARS:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=cols + ["family"])
        d = d[d["family"] == family].drop(columns=["family"])
        d["game_year"] = year
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


PITCH_COLS = ["pitcher", "game_year", "release_speed", "ivb", "hb_arm",
              "release_spin_rate", "is_whiff", "is_swing", "is_csw",
              "delta_run_exp", "estimated_woba_using_speedangle", "type"]


def outcome_row(g: pd.DataFrame) -> dict:
    swings = int(g["is_swing"].sum())
    contact = g[(g["type"] == "X")
                & g["estimated_woba_using_speedangle"].notna()]
    return {
        "pitches": int(len(g)),
        "pitchers": int(g["pitcher"].nunique()),
        "whiff_pct": 100 * float(g["is_whiff"].sum() / swings) if swings else np.nan,
        "csw_pct": 100 * float(g["is_csw"].mean()),
        "rv100": -100 * float(g["delta_run_exp"].mean()),
        "xwobacon": float(contact["estimated_woba_using_speedangle"].mean())
        if len(contact) else np.nan,
        "velo": float(g["release_speed"].mean()),
        "ivb": float(g["ivb"].mean()),
        "hb_arm": float(g["hb_arm"].mean()),
    }


def splitter_profile() -> tuple[pd.DataFrame, pd.DataFrame]:
    fs = load_family("FS", [c for c in PITCH_COLS if c != "game_year"])

    per_year = pd.DataFrame([
        {"game_year": y, **outcome_row(g)} for y, g in fs.groupby("game_year")
    ])

    # arsenal-level dispersion at the relaxed 50-pitch threshold
    ars = (fs.groupby(["pitcher", "game_year"])
           .agg(pitches=("release_speed", "size"),
                velo=("release_speed", "median"),
                ivb=("ivb", "median"), hb=("hb_arm", "median"),
                spin=("release_spin_rate", "median"))
           .reset_index())
    ars = ars[ars["pitches"] >= MIN_SPLITTER_PITCHES]
    disp = (ars.groupby("game_year")
            .agg(n_pitchers=("pitcher", "size"),
                 velo_sd=("velo", "std"), ivb_sd=("ivb", "std"),
                 hb_sd=("hb", "std"), spin_sd=("spin", "std"))
            .reset_index().round(3))
    return per_year.round(3), disp


def splitter_adopters() -> pd.DataFrame:
    """Where did new splitter throwers come from? Track their changeup usage."""
    rows = []
    usage = []
    for year in config.YEARS:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        d = pd.read_parquet(path, columns=["pitcher", "family"])
        tot = d.groupby("pitcher").size().rename("total")
        fam = (d.groupby(["pitcher", "family"]).size().rename("n")
               .reset_index().merge(tot, on="pitcher"))
        fam["share"] = fam["n"] / fam["total"]
        fam["game_year"] = year
        usage.append(fam)
    u = pd.concat(usage, ignore_index=True)

    fs = u[(u["family"] == "FS") & (u["n"] >= MIN_SPLITTER_PITCHES)]
    first_fs = fs.groupby("pitcher")["game_year"].min()
    for pitcher, y0 in first_fs.items():
        if y0 == config.YEARS[0]:
            continue  # cannot tell adoption from pre-existing use
        prev = u[(u["pitcher"] == pitcher) & (u["game_year"] == y0 - 1)]
        if prev.empty or prev["total"].iloc[0] < 200:
            continue
        ch_before = float(prev.loc[prev["family"] == "CH", "share"].sum())
        now = u[(u["pitcher"] == pitcher) & (u["game_year"] == y0)]
        ch_after = float(now.loc[now["family"] == "CH", "share"].sum())
        rows.append({"pitcher": pitcher, "adopted_year": int(y0),
                     "ch_share_before": ch_before, "ch_share_after": ch_after})
    ad = pd.DataFrame(rows)
    if ad.empty:
        return ad
    summary = (ad.groupby("adopted_year")
               .agg(n_adopters=("pitcher", "size"),
                    ch_before=("ch_share_before", "mean"),
                    ch_after=("ch_share_after", "mean"))
               .reset_index())
    summary["ch_drop_pp"] = 100 * (summary["ch_after"] - summary["ch_before"])
    return summary.round(4)


def deathball_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sl = load_family("SLV", [c for c in PITCH_COLS if c != "game_year"])
    sl = sl.dropna(subset=["release_speed", "ivb", "hb_arm"])

    is_db = ((sl["release_speed"] >= 85) & (sl["hb_arm"].abs() <= 3)
             & (sl["ivb"] <= -2))
    is_db_strict = ((sl["release_speed"] >= 85) & (sl["hb_arm"].abs() <= 2)
                    & (sl["ivb"] <= -4))
    sl["db"] = np.where(is_db_strict, "strict",
                        np.where(is_db, "loose", "other_slider"))

    per_year = []
    for (year, db), g in sl.groupby(["game_year", "db"]):
        per_year.append({"game_year": year, "class": db, **outcome_row(g)})
    per_year = pd.DataFrame(per_year)
    tot = per_year.groupby("game_year")["pitches"].transform("sum")
    per_year["share_of_sliders_pct"] = (100 * per_year["pitches"] / tot).round(2)

    # deathball vs. ordinary slider, same season contrast
    contrast = []
    for year, g in sl.groupby("game_year"):
        db_g, oth = g[g["db"] != "other_slider"], g[g["db"] == "other_slider"]
        if len(db_g) < 2000:
            continue
        a, b = outcome_row(db_g), outcome_row(oth)
        contrast.append({
            "game_year": year, "db_pitches": a["pitches"],
            "db_pitchers": db_g["pitcher"].nunique(),
            "whiff_edge_pp": round(a["whiff_pct"] - b["whiff_pct"], 2),
            "csw_edge_pp": round(a["csw_pct"] - b["csw_pct"], 2),
            "rv100_edge": round(a["rv100"] - b["rv100"], 3),
            "xwobacon_edge": round(a["xwobacon"] - b["xwobacon"], 4),
        })
    contrast = pd.DataFrame(contrast)

    # leading practitioners, most recent season
    last = sl[(sl["game_year"] == config.YEARS[-1]) & (sl["db"] != "other_slider")]
    names = D.pitcher_name_map()
    top = (last.groupby("pitcher")
           .agg(deathballs=("release_speed", "size"),
                velo=("release_speed", "mean"), ivb=("ivb", "mean"),
                hb=("hb_arm", "mean"),
                whiffs=("is_whiff", "sum"), swings=("is_swing", "sum"))
           .reset_index())
    top = top[top["deathballs"] >= 100]
    top["whiff_pct"] = (100 * top["whiffs"] / top["swings"]).round(1)
    top["pitcher_name"] = top["pitcher"].map(names).fillna(
        top["pitcher"].astype(str))
    top = (top.sort_values("deathballs", ascending=False).head(15)
           [["pitcher", "pitcher_name", "deathballs", "velo", "ivb", "hb",
             "whiff_pct"]].round(2))
    return per_year.round(3), contrast, top


def figure(split_year: pd.DataFrame, db_year: pd.DataFrame) -> None:
    fig, axes = P.facet_grid(3, ncols=3, width=4.1, height=3.3)

    ax = axes[0]
    ax.plot(split_year["game_year"], split_year["pitchers"],
            marker="o", color=P.SERIES[0], lw=1.8)
    P.style_axis(ax, title="Splitter practitioners",
                 ylabel="Pitchers throwing a splitter")
    P.year_axis(ax, config.YEARS)

    ax = axes[1]
    ax.plot(split_year["game_year"], split_year["whiff_pct"],
            marker="o", color=P.SERIES[1], lw=1.8, label="Splitter whiff%")
    P.style_axis(ax, title="Splitter whiff rate", ylabel="Whiff% per swing")
    P.year_axis(ax, config.YEARS)

    ax = axes[2]
    db = db_year[db_year["class"] != "other_slider"]
    db_tot = db.groupby("game_year")["share_of_sliders_pct"].sum()
    ax.plot(db_tot.index, db_tot.values, marker="o", color=P.SERIES[2], lw=1.8)
    P.style_axis(ax, title="Deathball share of sliders",
                 ylabel="% of slider-family pitches")
    P.year_axis(ax, config.YEARS)

    P.suptitle(fig, "Two recolonizations in progress",
               "A neglected pitch type (splitter) and a neglected shape cell "
               "inside a crowded family (the deathball)")
    P.finish(fig)
    P.save(fig, "fig15_splitter_deathball")


def main() -> None:
    split_year, split_disp = splitter_profile()
    D.save_result(split_year, "s8_splitter_by_year")
    D.save_result(split_disp, "s8_splitter_dispersion")
    print("=== splitter by season ===")
    print(split_year[["game_year", "pitches", "pitchers", "whiff_pct",
                      "csw_pct", "rv100", "xwobacon", "velo", "ivb"]]
          .to_string(index=False))
    print("\n=== splitter arsenal dispersion (>=50 pitches) ===")
    print(split_disp.to_string(index=False))

    adopters = splitter_adopters()
    if not adopters.empty:
        D.save_result(adopters, "s8_splitter_adopters")
        print("\n=== splitter adopters: changeup usage before/after ===")
        print(adopters.to_string(index=False))

    db_year, db_contrast, db_top = deathball_tables()
    D.save_result(db_year, "s8_deathball_by_year")
    D.save_result(db_contrast, "s8_deathball_contrast")
    D.save_result(db_top, "s8_deathball_practitioners")
    print("\n=== deathball share and outcomes ===")
    print(db_year[db_year["class"] != "other_slider"]
          [["game_year", "class", "pitches", "pitchers",
            "share_of_sliders_pct", "whiff_pct", "rv100"]].to_string(index=False))
    print("\n=== deathball vs ordinary slider ===")
    print(db_contrast.to_string(index=False))
    print("\n=== top practitioners, latest season ===")
    print(db_top.to_string(index=False))

    figure(split_year, db_year)
    D.write_meta("s8_splitter_deathball", {
        "min_splitter_pitches": MIN_SPLITTER_PITCHES,
        "deathball_loose": "velo>=85, |hb|<=3, ivb<=-2",
        "deathball_strict": "velo>=85, |hb|<=2, ivb<=-4",
    })


if __name__ == "__main__":
    main()
