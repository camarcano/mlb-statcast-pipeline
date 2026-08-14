"""Shared figure style.

Figures are rendered as PNGs on the light chart surface and embedded in the
HTML report inside a light-surface card, so they stay legible regardless of the
reader's theme. Colour usage follows the validated categorical order; where more
than three families appear at once the figure is faceted (small multiples) so
identity never rests on hue alone, and every figure has a matching CSV in
analysis/results/ acting as its table view.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis import config

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# validated categorical order (adjacent-pair gates pass in light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
POS = "#2a78d6"   # diverging cool pole
NEG = "#d03b3b"   # diverging warm pole
NEUTRAL = "#c3c2b7"

FAMILY_COLOR = {f: SERIES[i % len(SERIES)] for i, f in enumerate(config.FAMILY_ORDER)}

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK_SECONDARY,
    "axes.titlesize": 11,
    "axes.titleweight": "600",
    "axes.titlecolor": INK,
    "axes.labelsize": 9,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
    "legend.labelcolor": INK_SECONDARY,
    "lines.linewidth": 2.0,
    "lines.markersize": 5,
    "font.size": 9.5,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
})


def facet_grid(n: int, ncols: int = 4, width: float = 3.1, height: float = 2.5):
    """Small-multiple grid sized to the number of panels."""
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(width * ncols, height * nrows),
                             squeeze=False)
    flat = axes.ravel()
    for ax in flat[n:]:
        ax.set_visible(False)
    return fig, flat


def style_axis(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, loc="left", pad=8)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", visible=False)
    return ax


def year_axis(ax, years=None):
    years = years or config.YEARS
    ax.set_xticks(years)
    ax.set_xticklabels([str(y)[-2:] for y in years])
    ax.set_xlim(min(years) - 0.3, max(years) + 0.3)


def direct_label(ax, x, y, text, color, dx=0.08, **kw):
    """Label a series at its right end rather than in a legend box."""
    ax.annotate(text, xy=(x, y), xytext=(x + dx, y), color=color,
                fontsize=8.5, va="center", fontweight="600",
                annotation_clip=False, **kw)


def band(ax, x, lo, hi, color, alpha=0.14):
    ax.fill_between(x, lo, hi, color=color, alpha=alpha, linewidth=0)


def errorbars(ax, x, y, lo, hi, color, label=None, marker="o"):
    ax.errorbar(x, y, yerr=[np.asarray(y) - np.asarray(lo),
                            np.asarray(hi) - np.asarray(y)],
                fmt=marker, color=color, ecolor=color, elinewidth=1.4,
                capsize=0, markersize=6, label=label,
                markeredgecolor=SURFACE, markeredgewidth=1.2)


def zero_line(ax, horizontal=True):
    if horizontal:
        ax.axhline(0, color=AXIS, linewidth=1.0, zorder=1)
    else:
        ax.axvline(0, color=AXIS, linewidth=1.0, zorder=1)


def suptitle(fig, title, subtitle=None):
    """Left-aligned title with an optional deck line beneath it.

    Positions are in figure coordinates measured down from the top, so the deck
    never collides with the title regardless of figure height.
    """
    h = fig.get_size_inches()[1]
    title_y = 1 - 0.28 / h
    fig.text(0.008, title_y, title, ha="left", va="top",
             fontsize=13, fontweight="600", color=INK)
    if subtitle:
        fig.text(0.008, title_y - 0.30 / h, subtitle, ha="left", va="top",
                 fontsize=9, color=INK_SECONDARY)


def finish(fig, bottom: float = 0.0):
    """tight_layout leaving exact room for the title block (and legend)."""
    h = fig.get_size_inches()[1]
    top = 1 - 0.70 / h
    fig.tight_layout(rect=[0, bottom, 1, top])


def save(fig, name: str) -> str:
    """Write a figure to analysis/figures/<name>.png and close it."""
    path = config.FIGURES_DIR / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return str(path)
