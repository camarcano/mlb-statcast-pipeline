"""Statistical primitives shared by the study scripts.

Everything here is deliberately explicit rather than delegated to a framework:
the dispersion estimators, the pitcher-clustered bootstrap, and the shrinkage
estimators are the load-bearing parts of the analysis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps
from sklearn.covariance import LedoitWolf

from analysis import config


# --------------------------------------------------------------------------
# dispersion estimators
# --------------------------------------------------------------------------
def robust_cv(x: np.ndarray) -> float:
    """MAD-based coefficient of variation; scale-free, outlier-resistant."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return np.nan
    med = np.median(x)
    if not np.isfinite(med) or abs(med) < 1e-9:
        return np.nan
    mad = np.median(np.abs(x - med)) * 1.4826
    return float(mad / abs(med))


def iqr(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 4:
        return np.nan
    return float(np.percentile(x, 75) - np.percentile(x, 25))


def sd(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return np.nan
    return float(np.std(x, ddof=1))


def mad_scale(x: np.ndarray) -> float:
    """Median absolute deviation on the SD scale."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return np.nan
    return float(np.median(np.abs(x - np.median(x))) * 1.4826)


def circular_sd(degrees: np.ndarray) -> float:
    """Circular standard deviation in degrees (for spin axis)."""
    d = np.asarray(degrees, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 3:
        return np.nan
    rad = np.deg2rad(d)
    R = np.hypot(np.mean(np.sin(rad)), np.mean(np.cos(rad)))
    R = min(max(R, 1e-12), 1 - 1e-12)
    return float(np.rad2deg(np.sqrt(-2.0 * np.log(R))))


DISPERSION_FUNCS = {"sd": sd, "iqr": iqr, "robust_cv": robust_cv, "mad": mad_scale}


# --------------------------------------------------------------------------
# resampling
# --------------------------------------------------------------------------
def cluster_bootstrap_ci(
    df: pd.DataFrame,
    value_col: str,
    stat_func,
    cluster_col: str = "pitcher",
    reps: int = config.BOOT_REPS,
    alpha: float = 0.05,
    seed: int = config.SEED,
) -> tuple[float, float, float]:
    """Percentile CI for a dispersion statistic, resampling whole clusters.

    Pitchers, not pitches, are the independent unit: a pitcher contributes many
    correlated observations, so naive bootstrap CIs would be far too narrow.
    """
    rng = np.random.default_rng(seed)
    point = stat_func(df[value_col].to_numpy())
    clusters = df[cluster_col].to_numpy()
    uniq = np.unique(clusters)
    if uniq.size < 5:
        return point, np.nan, np.nan
    idx_by_cluster = {c: np.flatnonzero(clusters == c) for c in uniq}
    values = df[value_col].to_numpy()

    draws = np.empty(reps)
    for i in range(reps):
        picked = rng.choice(uniq, size=uniq.size, replace=True)
        idx = np.concatenate([idx_by_cluster[c] for c in picked])
        draws[i] = stat_func(values[idx])
    draws = draws[np.isfinite(draws)]
    if draws.size < 50:
        return point, np.nan, np.nan
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(point), float(lo), float(hi)


def cluster_bootstrap_contrast(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    value_col: str,
    stat_func,
    cluster_col: str = "pitcher",
    reps: int = config.BOOT_REPS,
    alpha: float = 0.05,
    seed: int = config.SEED,
    relative: bool = True,
) -> dict:
    """Bootstrap CI for stat(B) - stat(A), or the ratio when `relative`.

    Clusters are resampled independently within each year, which is the right
    null for "is dispersion different in year B than year A".
    """
    rng = np.random.default_rng(seed)
    fa, fb = stat_func(df_a[value_col].to_numpy()), stat_func(df_b[value_col].to_numpy())
    point = (fb / fa - 1.0) if (relative and fa) else (fb - fa)

    def _prep(d):
        cl = d[cluster_col].to_numpy()
        u = np.unique(cl)
        return u, {c: np.flatnonzero(cl == c) for c in u}, d[value_col].to_numpy()

    ua, ia, va = _prep(df_a)
    ub, ib, vb = _prep(df_b)
    if ua.size < 5 or ub.size < 5:
        return {"point": point, "lo": np.nan, "hi": np.nan, "p_two_sided": np.nan}

    draws = np.empty(reps)
    for i in range(reps):
        sa = va[np.concatenate([ia[c] for c in rng.choice(ua, ua.size, replace=True)])]
        sb = vb[np.concatenate([ib[c] for c in rng.choice(ub, ub.size, replace=True)])]
        qa, qb = stat_func(sa), stat_func(sb)
        draws[i] = (qb / qa - 1.0) if (relative and qa) else (qb - qa)
    draws = draws[np.isfinite(draws)]
    if draws.size < 50:
        return {"point": point, "lo": np.nan, "hi": np.nan, "p_two_sided": np.nan}
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    # two-sided bootstrap p-value: how far is 0 into the tail of the draws
    frac = float(np.mean(draws <= 0)) if point > 0 else float(np.mean(draws >= 0))
    p = min(1.0, 2 * max(frac, 1.0 / (draws.size + 1)))
    return {"point": float(point), "lo": float(lo), "hi": float(hi), "p_two_sided": p}


# --------------------------------------------------------------------------
# hypothesis tests
# --------------------------------------------------------------------------
def brown_forsythe(groups: list[np.ndarray]) -> tuple[float, float]:
    """Levene's test on medians — equality of variance across years."""
    clean = [np.asarray(g, float)[np.isfinite(g)] for g in groups]
    clean = [g for g in clean if g.size >= 5]
    if len(clean) < 2:
        return np.nan, np.nan
    stat, p = sps.levene(*clean, center="median")
    return float(stat), float(p)


def theil_sen_slope(x: np.ndarray, y: np.ndarray) -> dict:
    """Robust monotone trend estimate with CI (per unit of x)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return {"slope": np.nan, "lo": np.nan, "hi": np.nan}
    slope, intercept, lo, hi = sps.theilslopes(y[m], x[m], 0.95)
    return {"slope": float(slope), "intercept": float(intercept),
            "lo": float(lo), "hi": float(hi)}


def bh_fdr(pvals: np.ndarray, q: float = config.FDR_Q) -> np.ndarray:
    """Benjamini-Hochberg: returns a boolean 'significant' mask."""
    p = np.asarray(pvals, float)
    ok = np.isfinite(p)
    out = np.zeros(p.shape, bool)
    if ok.sum() == 0:
        return out
    idx = np.flatnonzero(ok)
    order = idx[np.argsort(p[idx])]
    m = order.size
    thresh = q * (np.arange(1, m + 1) / m)
    passed = p[order] <= thresh
    if passed.any():
        cutoff = np.max(np.flatnonzero(passed))
        out[order[: cutoff + 1]] = True
    return out


# --------------------------------------------------------------------------
# multivariate volume
# --------------------------------------------------------------------------
def log_det_cov(X: np.ndarray, shrink: bool = True) -> float:
    """Log generalised variance — the log-volume of the shape cloud.

    Ledoit-Wolf shrinkage keeps the estimate stable at the n/p ratios we have
    (a few hundred pitchers, 7-8 features).
    """
    X = np.asarray(X, float)
    X = X[np.isfinite(X).all(axis=1)]
    if X.shape[0] < X.shape[1] + 5:
        return np.nan
    cov = LedoitWolf().fit(X).covariance_ if shrink else np.cov(X, rowvar=False)
    sign, logdet = np.linalg.slogdet(cov)
    return float(logdet) if sign > 0 else np.nan


def participation_ratio(X: np.ndarray) -> float:
    """Effective dimensionality: (sum lambda)^2 / sum(lambda^2), in [1, p]."""
    X = np.asarray(X, float)
    X = X[np.isfinite(X).all(axis=1)]
    if X.shape[0] < X.shape[1] + 5:
        return np.nan
    ev = np.linalg.eigvalsh(np.cov(X, rowvar=False))
    ev = ev[ev > 1e-12]
    if ev.size == 0:
        return np.nan
    return float(ev.sum() ** 2 / np.sum(ev ** 2))


def pcs_for_variance(X: np.ndarray, frac: float = 0.90) -> float:
    X = np.asarray(X, float)
    X = X[np.isfinite(X).all(axis=1)]
    if X.shape[0] < X.shape[1] + 5:
        return np.nan
    ev = np.sort(np.linalg.eigvalsh(np.cov(X, rowvar=False)))[::-1]
    ev = ev[ev > 0]
    if ev.size == 0:
        return np.nan
    return float(np.searchsorted(np.cumsum(ev) / ev.sum(), frac) + 1)


def gaussian_entropy(X: np.ndarray) -> float:
    """Differential entropy of the fitted Gaussian, in nats."""
    ld = log_det_cov(X)
    if not np.isfinite(ld):
        return np.nan
    p = X.shape[1]
    return float(0.5 * (p * np.log(2 * np.pi * np.e) + ld))


def shannon_entropy(proportions: np.ndarray) -> float:
    p = np.asarray(proportions, float)
    p = p[p > 0]
    if p.size == 0:
        return np.nan
    p = p / p.sum()
    return float(-np.sum(p * np.log(p)))


# --------------------------------------------------------------------------
# empirical Bayes shrinkage
# --------------------------------------------------------------------------
def eb_shrink_rate(successes: np.ndarray, trials: np.ndarray) -> np.ndarray:
    """Beta-binomial shrinkage of rates toward the pooled mean.

    Prior strength is estimated by method of moments on the observed rate
    distribution, so pitchers with 100 pitches are pulled harder than pitchers
    with 2,000.
    """
    s = np.asarray(successes, float)
    n = np.asarray(trials, float)
    ok = n > 0
    if ok.sum() < 10:
        return np.where(ok, s / np.maximum(n, 1), np.nan)
    p = s[ok] / n[ok]
    mu = float(np.average(p, weights=n[ok]))
    var = float(np.average((p - mu) ** 2, weights=n[ok]))
    within = mu * (1 - mu) * float(np.mean(1.0 / n[ok]))
    between = max(var - within, 1e-9)
    k = max(mu * (1 - mu) / between - 1.0, 1.0)  # prior sample size
    a, b = mu * k, (1 - mu) * k
    out = np.full(s.shape, np.nan)
    out[ok] = (s[ok] + a) / (n[ok] + a + b)
    return out


def eb_shrink_mean(values: np.ndarray, counts: np.ndarray,
                   obs_sd: float | None = None) -> np.ndarray:
    """Normal-normal shrinkage of per-unit means toward the grand mean."""
    v = np.asarray(values, float)
    n = np.asarray(counts, float)
    ok = np.isfinite(v) & (n > 0)
    if ok.sum() < 10:
        return v
    mu = float(np.average(v[ok], weights=n[ok]))
    total_var = float(np.average((v[ok] - mu) ** 2, weights=n[ok]))
    if obs_sd is None:
        # infer within-unit noise from the count-weighted variance structure
        obs_sd = np.sqrt(max(total_var, 1e-12)) * np.sqrt(float(np.mean(n[ok])))
    within = obs_sd ** 2 / np.maximum(n, 1)
    between = max(total_var - float(np.mean(within[ok])), 1e-12)
    w = between / (between + within)
    out = v.copy()
    out[ok] = mu + w[ok] * (v[ok] - mu)
    return out


def weighted_mean(values, weights) -> float:
    v, w = np.asarray(values, float), np.asarray(weights, float)
    m = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if m.sum() == 0:
        return np.nan
    return float(np.average(v[m], weights=w[m]))
