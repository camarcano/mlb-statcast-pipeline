"""Measuring how unusual a pitch is relative to its league-year peers.

Two complementary scores, because each has a distinct failure mode:

* Mahalanobis distance from a robustly estimated league centre. Global, cheap,
  but assumes an elliptical cloud, so a pitch sitting in a sparse pocket
  *inside* the cloud scores as ordinary.
* Mean distance to the k nearest other pitchers. Local, captures sparse
  pockets, but noisier in the tails.

Both are converted to within-family-year percentiles so they are comparable
across families and seasons.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import MinCovDet
from sklearn.neighbors import NearestNeighbors

from analysis import config


def mahalanobis_scores(X: np.ndarray, seed: int = config.SEED) -> np.ndarray:
    """Robust Mahalanobis distance from the league centre.

    MinCovDet fits the centre and covariance on the densest half of the data,
    so the "normal" reference is not dragged toward the outliers being measured.
    """
    X = np.asarray(X, float)
    ok = np.isfinite(X).all(axis=1)
    out = np.full(X.shape[0], np.nan)
    if ok.sum() < max(30, 3 * X.shape[1]):
        return out
    try:
        mcd = MinCovDet(random_state=seed, support_fraction=0.75).fit(X[ok])
        out[ok] = np.sqrt(mcd.mahalanobis(X[ok]))
    except Exception:
        # fall back to the classical estimate if MCD fails to converge
        c = np.cov(X[ok], rowvar=False)
        inv = np.linalg.pinv(c)
        d = X[ok] - X[ok].mean(axis=0)
        out[ok] = np.sqrt(np.einsum("ij,jk,ik->i", d, inv, d))
    return out


def knn_isolation(X: np.ndarray, groups: np.ndarray | None = None,
                  k: int = config.KNN_K) -> np.ndarray:
    """Mean distance to the k nearest neighbours, excluding same-pitcher rows.

    Excluding a pitcher's own other pitches matters: a pitcher with a tight
    arsenal would otherwise look 'crowded' by himself.
    """
    X = np.asarray(X, float)
    ok = np.isfinite(X).all(axis=1)
    out = np.full(X.shape[0], np.nan)
    n = int(ok.sum())
    if n < k + 5:
        return out
    Xo = X[ok]
    # ask for extra neighbours so we can drop same-group ones and still have k
    n_query = min(n, k + 25)
    nn = NearestNeighbors(n_neighbors=n_query).fit(Xo)
    dist, idx = nn.kneighbors(Xo)
    if groups is None:
        out[ok] = dist[:, 1:k + 1].mean(axis=1)
        return out
    go = np.asarray(groups)[ok]
    means = np.empty(n)
    for i in range(n):
        mask = go[idx[i]] != go[i]
        d = dist[i][mask]
        means[i] = d[:k].mean() if d.size >= 1 else np.nan
    out[ok] = means
    return out


def score_arsenal(arsenal: pd.DataFrame, features: list[str],
                  group_cols: tuple[str, str] = ("family", "game_year")) -> pd.DataFrame:
    """Attach uniqueness scores and within-group percentiles to arsenal rows.

    Scaling is done within family-year: "unusual" is defined relative to the
    league a hitter actually faced that season, which is the quantity the
    hypothesis is about.
    """
    df = arsenal.copy()
    df["uniq_maha"] = np.nan
    df["uniq_knn"] = np.nan

    for _, idx in df.groupby(list(group_cols)).groups.items():
        sub = df.loc[idx, features]
        med = sub.median()
        mad = (sub - med).abs().median() * 1.4826
        mad = mad.replace(0, np.nan).fillna(sub.std(ddof=1)).replace(0, 1.0)
        Z = ((sub - med) / mad).to_numpy(float)
        df.loc[idx, "uniq_maha"] = mahalanobis_scores(Z)
        df.loc[idx, "uniq_knn"] = knn_isolation(
            Z, groups=df.loc[idx, "pitcher"].to_numpy()
        )

    for col in ("uniq_maha", "uniq_knn"):
        df[col + "_pct"] = (
            df.groupby(list(group_cols))[col]
            .rank(pct=True, method="average")
        )
    df["uniq_pct"] = df["uniq_maha_pct"]
    df["uniq_decile"] = np.ceil(df["uniq_pct"] * 10).clip(1, 10)
    return df
