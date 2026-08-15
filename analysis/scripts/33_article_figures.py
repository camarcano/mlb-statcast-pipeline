"""Figures for the long-form article.

The study figures are multi-panel and built for a reader who wants the whole
model. These are the opposite: one idea per chart, no panel grids, big enough
type to survive being dropped into a Word page at 6.5 inches wide.

Palette slots and surface come from analysis/lib/plotting.py, which already
matches the validated reference palette.
"""
from __future__ import annotations

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import plotting as P

BLUE, ORANGE = P.SERIES[0], P.SERIES[1]
R = config.RESULTS_DIR


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(R / f"{name}.csv")


def finish(fig, ax_list, name: str, title: str, subtitle: str) -> None:
    for ax in np.atleast_1d(ax_list):
        ax.set_facecolor(P.SURFACE)
    fig.patch.set_facecolor(P.SURFACE)
    fig.suptitle(title, x=0.012, y=0.985, ha="left", fontsize=14.5,
                 fontweight="bold", color=P.INK)
    fig.text(0.012, 0.915, subtitle, ha="left", fontsize=10,
             color=P.INK_SECONDARY)
    fig.tight_layout(rect=[0, 0, 1, 0.87])
    fig.savefig(config.FIGURES_DIR / f"{name}.png", dpi=200,
                facecolor=P.SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.png")


def fig_convergence() -> None:
    """Share of pitchers drifting toward the league centre, against the noise floor."""
    d = read("s3_directional_convergence")
    yoy = d[d["series"] == "year_over_year"].reset_index(drop=True)
    null = d[d["series"] == "within_year_null"].reset_index(drop=True)
    x = np.arange(len(yoy))
    labels = [p.replace("->", "→\n") for p in yoy["year_pair"]]

    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    ax.bar(x, 100 * yoy["frac_toward_centre"], width=0.56, color=BLUE,
           zorder=3, label="Pitchers who moved toward the league average")
    # the null is a benchmark, not a peer series, so it stays neutral
    for i, v in enumerate(100 * null["frac_toward_centre"]):
        ax.plot([i - 0.34, i + 0.34], [v, v], color=P.INK_SECONDARY, lw=2.2,
                zorder=4, solid_capstyle="round",
                label="What random noise alone would produce" if i == 0 else None)
    for i, v in enumerate(100 * yoy["frac_toward_centre"]):
        ax.text(i, v + 0.9, f"{v:.0f}%", ha="center", fontsize=10.5,
                fontweight="bold", color=P.INK)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylim(0, 82)
    ax.set_ylabel("Share of pitchers", fontsize=10)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="y", color=P.GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(P.AXIS)
    # sits above the plot area: inside it, the legend covered a bar label
    ax.legend(frameon=False, fontsize=9.5, loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=2)
    finish(fig, ax, "art01_convergence",
           "Every season, about two-thirds of pitchers move toward the middle",
           "Measured on each pitcher's own pitch, against a noise floor built "
           "from split halves of the same season.")


def fig_usage_value() -> None:
    """Connected scatter: what happened to the sweeper and the changeup."""
    d = read("s4_family_ecology")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=True)

    panels = (("SLV", ORANGE, "Slider / Sweeper", axes[0]),
              ("CH", BLUE, "Changeup", axes[1]))
    for fam, color, label, ax in panels:
        g = d[d["family"] == fam].sort_values("game_year")
        ax.plot(g["usage_share"], g["rv100_rel"], color=color, lw=2,
                marker="o", ms=7, zorder=3)
        # cycle the label position through four offsets: seasons can sit almost
        # on top of each other when usage barely moves, and a simple up/down
        # alternation still collided
        offsets = [(0, 11), (0, -17), (20, -4), (-20, -4)]
        for k, (_, r) in enumerate(g.iterrows()):
            ax.annotate(f"’{str(int(r['game_year']))[2:]}",
                        (r["usage_share"], r["rv100_rel"]),
                        textcoords="offset points", xytext=offsets[k % 4],
                        ha="center", fontsize=9, color=P.INK_SECONDARY)
        ax.axhline(0, color=P.AXIS, lw=1.1, ls="--", zorder=1)
        ax.set_title(label, fontsize=11.5, fontweight="bold", color=color,
                     loc="left", pad=8)
        ax.set_xlabel("Share of all pitches thrown", fontsize=10)
        # the changeup moves inside a single percentage point, so integer ticks
        # would print "11%" four times
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.1f}%")
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))
        ax.margins(x=0.26, y=0.30)
        ax.grid(color=P.GRID, lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(P.AXIS)

    axes[0].set_ylabel("Run value vs league average\n(higher is better for the pitcher)",
                       fontsize=10)
    axes[0].text(0.02, 0.02, "league average", transform=axes[0].transAxes,
                 fontsize=9, color=P.INK_SECONDARY)
    finish(fig, axes, "art02_usage_value",
           "The sweeper got popular and got worse. The changeup did the reverse.",
           "Each dot is one season, 2021 through 2026. Right means more pitchers "
           "threw it; down means it stopped working. Note the two panels cover "
           "different usage ranges.")


def fig_uniqueness() -> None:
    """Whiff rate across uniqueness deciles."""
    d = read("s5_decile_gradient")
    g = d[d["outcome"] == "whiff_pct"].sort_values("decile")

    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    ax.errorbar(g["decile"], g["mean"],
                yerr=[g["mean"] - g["lo"], g["hi"] - g["mean"]],
                fmt="o", ms=8, lw=0, elinewidth=1.6, capsize=3,
                color=BLUE, ecolor=P.AXIS, zorder=3)
    # least-squares guide line, drawn thin so the points stay the subject
    m, b = np.polyfit(g["decile"], g["mean"], 1)
    ax.plot(g["decile"], m * g["decile"] + b, color=BLUE, lw=1.4, alpha=0.5,
            zorder=2)

    ax.set_xticks(range(1, 11))
    ax.set_xlabel("How unusual the pitch is, in tenths of the league "
                  "(1 = most ordinary, 10 = strangest)", fontsize=10)
    ax.set_ylabel("Whiff rate per swing", fontsize=10)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.1f}%")
    ax.grid(axis="y", color=P.GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(P.AXIS)
    finish(fig, ax, "art03_uniqueness",
           "The stranger the pitch, the more bats it misses",
           "Every pitcher-season sorted into tenths by how far its shape sits "
           "from the league norm. Bars are 95% intervals.")


def fig_familiarity() -> None:
    """Whiff rate against how much of that shape the hitter has seen lately."""
    d = read("s7_exposure_bins")
    d = d[d["split"] == "all"].copy()
    # The 21-40 bin holds under 500 pitches and is almost entirely fastballs,
    # so its rate bounces back up for reasons that have nothing to do with
    # familiarity. The controlled model in the caption handles that; a raw
    # chart cannot, so the bin is left out rather than explained away.
    d = d[d["exposure_bin"] != "21-40"]
    col = "whiff_pct"

    fig, ax = plt.subplots(figsize=(9.2, 4.3))
    x = np.arange(len(d))
    ax.plot(x, d[col], color=BLUE, lw=2.4, marker="o", ms=9, zorder=3)
    for i, v in enumerate(d[col]):
        ax.text(i, v + 0.26, f"{v:.1f}%", ha="center", fontsize=10,
                fontweight="bold", color=P.INK)

    ax.set_xticks(x)
    ax.set_xticklabels(d.iloc[:, 0].astype(str), fontsize=10)
    ax.set_xlabel("Pitches of that same shape the hitter faced in the previous "
                  "30 days", fontsize=10)
    ax.set_ylabel("Whiff rate per swing", fontsize=10)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="y", color=P.GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(P.AXIS)
    finish(fig, ax, "art04_familiarity",
           "A pitch works worse once the hitter has seen it lately",
           "Raw rates. The controlled model, which holds the hitter and the "
           "count fixed, puts the cost at 0.46 points of whiff per doubling "
           "of recent exposure.")


if __name__ == "__main__":
    print("article figures:")
    fig_convergence()
    fig_usage_value()
    fig_uniqueness()
    fig_familiarity()
