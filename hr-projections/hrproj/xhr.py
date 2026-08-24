"""Expected home runs from contact quality.

A league-wide empirical grid over exit velocity, launch angle and pull-relative
spray angle gives every batted ball a home run probability. Summing those over a
batter's batted balls yields xHR - what their contact deserved, independent of
how many balls happened to clear the wall.

Spray is in the grid deliberately: a 105 mph fly ball at 28 degrees is a home run
far more often when it is pulled than when it is hit the other way, and an
EV/LA-only grid therefore under-credits exactly the pull-heavy profiles that
decide a home run race.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from hrproj.config import ModelParams

EV_MIN, EV_MAX = 40.0, 125.0
LA_MIN, LA_MAX = -30.0, 60.0

# Pull-relative spray buckets, in degrees: oppo | center | pull.
SPRAY_EDGES = (-15.0, 15.0)
N_SPRAY = 3


def spray_bucket(spray: pd.Series) -> np.ndarray:
    """0 = oppo, 1 = center, 2 = pull. Missing spray becomes -1 (pooled)."""
    out = np.full(len(spray), -1, dtype=int)
    vals = spray.to_numpy(dtype=float)
    known = ~np.isnan(vals)
    out[known & (vals < SPRAY_EDGES[0])] = 0
    out[known & (vals >= SPRAY_EDGES[0]) & (vals <= SPRAY_EDGES[1])] = 1
    out[known & (vals > SPRAY_EDGES[1])] = 2
    return out


def _gaussian_kernel(sigma_bins: float) -> np.ndarray:
    if sigma_bins <= 0:
        return np.array([1.0])
    radius = max(1, int(np.ceil(3 * sigma_bins)))
    x = np.arange(-radius, radius + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma_bins) ** 2)
    return k / k.sum()


def _smooth2d(grid: np.ndarray, ev_kernel: np.ndarray, la_kernel: np.ndarray) -> np.ndarray:
    out = np.apply_along_axis(lambda row: np.convolve(row, ev_kernel, mode="same"), 0, grid)
    out = np.apply_along_axis(lambda row: np.convolve(row, la_kernel, mode="same"), 1, out)
    return out


@dataclass
class HRGrid:
    """Smoothed HR probability by (spray bucket, EV bin, LA bin)."""

    prob_2d: np.ndarray          # (n_ev, n_la)
    prob_3d: np.ndarray          # (N_SPRAY, n_ev, n_la)
    ev_edges: np.ndarray
    la_edges: np.ndarray

    def _indices(self, ev: np.ndarray, la: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        valid = np.isfinite(ev) & np.isfinite(la)
        ev_i = np.clip(
            np.digitize(ev, self.ev_edges) - 1, 0, self.prob_2d.shape[0] - 1
        )
        la_i = np.clip(
            np.digitize(la, self.la_edges) - 1, 0, self.prob_2d.shape[1] - 1
        )
        return ev_i, la_i, valid

    def probability(
        self, ev: np.ndarray, la: np.ndarray, bucket: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """HR probability for each batted ball. Non-finite inputs return 0."""
        ev = np.asarray(ev, dtype=float)
        la = np.asarray(la, dtype=float)
        ev_i, la_i, valid = self._indices(ev, la)

        out = self.prob_2d[ev_i, la_i]
        if bucket is not None:
            bucket = np.asarray(bucket, dtype=int)
            has_spray = bucket >= 0
            if has_spray.any():
                out = out.copy()
                out[has_spray] = self.prob_3d[
                    bucket[has_spray], ev_i[has_spray], la_i[has_spray]
                ]
        return np.where(valid, out, 0.0)


def build_grid(bbe: pd.DataFrame, params: ModelParams) -> HRGrid:
    """Fit the grid on batted balls. `bbe` needs launch_speed, launch_angle, spray, is_hr."""
    ev_edges = np.arange(EV_MIN, EV_MAX + params.ev_bin, params.ev_bin)
    la_edges = np.arange(LA_MIN, LA_MAX + params.la_bin, params.la_bin)
    shape = (len(ev_edges) - 1, len(la_edges) - 1)

    if bbe.empty:
        zeros = np.zeros(shape)
        return HRGrid(zeros, np.zeros((N_SPRAY, *shape)), ev_edges, la_edges)

    ev = bbe["launch_speed"].to_numpy(dtype=float)
    la = bbe["launch_angle"].to_numpy(dtype=float)
    hr = bbe["is_hr"].to_numpy(dtype=float)
    bucket = spray_bucket(bbe["spray"])

    ev_kernel = _gaussian_kernel(params.ev_sigma / params.ev_bin)
    la_kernel = _gaussian_kernel(params.la_sigma / params.la_bin)

    counts, _, _ = np.histogram2d(ev, la, bins=[ev_edges, la_edges])
    hits, _, _ = np.histogram2d(ev, la, bins=[ev_edges, la_edges], weights=hr)
    counts_s = _smooth2d(counts, ev_kernel, la_kernel)
    hits_s = _smooth2d(hits, ev_kernel, la_kernel)
    prob_2d = np.divide(hits_s, counts_s, out=np.zeros(shape), where=counts_s > 0)

    prob_3d = np.zeros((N_SPRAY, *shape))
    for b in range(N_SPRAY):
        sel = bucket == b
        if not sel.any():
            prob_3d[b] = prob_2d
            continue
        c, _, _ = np.histogram2d(ev[sel], la[sel], bins=[ev_edges, la_edges])
        h, _, _ = np.histogram2d(ev[sel], la[sel], bins=[ev_edges, la_edges], weights=hr[sel])
        c_s = _smooth2d(c, ev_kernel, la_kernel)
        h_s = _smooth2d(h, ev_kernel, la_kernel)
        p_b = np.divide(h_s, c_s, out=np.zeros(shape), where=c_s > 0)
        # Pool toward the spray-agnostic grid wherever the bucket is thin.
        w = c_s / (c_s + params.spray_min_n)
        prob_3d[b] = w * p_b + (1 - w) * prob_2d

    return HRGrid(prob_2d, prob_3d, ev_edges, la_edges)


def expected_hr_per_pa(pa: pd.DataFrame, grid: HRGrid) -> pd.Series:
    """xHR contribution of every plate appearance (0 for anything not put in play)."""
    out = np.zeros(len(pa))
    bbe_mask = pa["is_bbe"].to_numpy()
    if bbe_mask.any():
        sub = pa.loc[bbe_mask]
        out[bbe_mask] = grid.probability(
            sub["launch_speed"].to_numpy(dtype=float),
            sub["launch_angle"].to_numpy(dtype=float),
            spray_bucket(sub["spray"]),
        )
    return pd.Series(out, index=pa.index)


def league_hr_per_bbia(pa: pd.DataFrame) -> float:
    """League home runs per 100+ mph air ball, over whatever window `pa` covers.

    Recomputed rather than hardcoded: it moved from .483 to .531 across the 2026
    season as the league's home run environment warmed up.
    """
    count = float(pa["is_bbia100"].sum())
    if count <= 0:
        return 0.0
    return float(pa["is_hr"].sum()) / count


def bbia_expected_hr(pa: pd.DataFrame, league_ratio: float) -> pd.Series:
    """Expected home runs per plate appearance from hard air contact alone.

    Every 100+ mph air ball is worth the league's home run rate on such contact,
    and nothing else scores. Blunter than the grid - no spray, no credit for a
    98 mph liner - but calibrated to the league total by construction, and a
    better predictor of future home runs than past home runs are.
    """
    return pd.Series(
        pa["is_bbia100"].to_numpy(dtype=float) * league_ratio, index=pa.index
    )


def blend_features(
    grid_xhr: pd.Series, bbia_xhr: pd.Series, weight: float
) -> pd.Series:
    """Mix the two expected-home-run estimators. `weight` is the BBIA share."""
    weight = float(np.clip(weight, 0.0, 1.0))
    if weight == 0.0:
        return grid_xhr
    if weight == 1.0:
        return bbia_xhr
    return (1.0 - weight) * grid_xhr + weight * bbia_xhr


def expected_hr_feature(pa: pd.DataFrame, params) -> pd.Series:
    """The expected-home-run series the rate model consumes.

    The grid on its own at `bbia_weight` 0, mixed with the 100+ mph air-ball
    estimator above it. Both `build_projection` and `run_backtest` go through
    here so a weight set on the parameters cannot be honoured by one and
    silently ignored by the other.
    """
    grid = build_grid(pa[pa["is_bbe"]], params)
    grid_xhr = expected_hr_per_pa(pa, grid)

    if params.bbia_weight <= 0:
        return grid_xhr

    bbia = bbia_expected_hr(pa, league_hr_per_bbia(pa))
    return blend_features(grid_xhr, bbia, params.bbia_weight)
