"""S5 - Do unusual pitches perform better?

The core of the hypothesis. Uniqueness is scored at the arsenal grain against
the same-family, same-season league distribution, then related to outcomes
through four models that fail in different ways:

1. Decile gradient -- assumption-free, but says nothing about why.
2. Spline regression with controls -- flexible shape, but between-pitcher.
3. Within/between decomposition -- the within estimator holds the pitcher
   fixed and asks whether his own pitch improves as it drifts from the norm;
   the between estimator asks whether the pitchers who own unusual pitches are
   simply better. This separates the effect from the selection.
4. Gradient boosting on the pitch grain -- does uniqueness add predictive
   signal beyond velocity, movement and location?

Uniqueness is a deterministic function of the shape features, so none of these
identify a causal effect on its own; S6 and S7 supply the leverage.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import partial_dependence
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D
from analysis.lib import outcomes as oc
from analysis.lib import plotting as P
from analysis.lib import stats as S
from analysis.lib import uniqueness as U

warnings.filterwarnings("ignore")


def add_shrunk_outcomes(ars: pd.DataFrame) -> pd.DataFrame:
    """Empirical-Bayes shrinkage within family-year."""
    out = []
    for _, g in ars.groupby(["family", "game_year"]):
        g = g.copy()
        g["whiff_pct_eb"] = 100 * S.eb_shrink_rate(
            g["whiffs"].to_numpy(), g["swings"].to_numpy())
        g["csw_pct_eb"] = 100 * S.eb_shrink_rate(
            g["csw"].to_numpy(), g["pitches"].to_numpy())
        g["rv100_eb"] = S.eb_shrink_mean(
            g["rv100"].to_numpy(), g["pitches"].to_numpy())
        g["xwobacon_eb"] = S.eb_shrink_mean(
            g["xwobacon"].to_numpy(), g["n_xwoba"].to_numpy())
        out.append(g)
    return pd.concat(out, ignore_index=True)


def decile_gradient(ars: pd.DataFrame, reps: int) -> pd.DataFrame:
    """Outcome by uniqueness decile, with pitcher-bootstrap CIs."""
    rng = np.random.default_rng(config.SEED)
    rows = []
    for col in ["whiff_pct_eb", "csw_pct_eb", "rv100_eb", "xwobacon_eb"]:
        for dec, g in ars.groupby("uniq_decile"):
            v = g[col].dropna().to_numpy()
            if v.size < 20:
                continue
            draws = np.array([rng.choice(v, v.size, replace=True).mean()
                              for _ in range(reps)])
            rows.append({
                "outcome": col.replace("_eb", ""), "decile": int(dec),
                "n": int(v.size), "mean": float(v.mean()),
                "lo": float(np.percentile(draws, 2.5)),
                "hi": float(np.percentile(draws, 97.5)),
            })
    df = pd.DataFrame(rows)
    # top-vs-bottom contrast per outcome
    contrasts = []
    for outcome, g in df.groupby("outcome"):
        lo_d = g[g["decile"] == g["decile"].min()]
        hi_d = g[g["decile"] == g["decile"].max()]
        if lo_d.empty or hi_d.empty:
            continue
        contrasts.append({
            "outcome": outcome,
            "bottom_decile_mean": float(lo_d["mean"].iloc[0]),
            "top_decile_mean": float(hi_d["mean"].iloc[0]),
            "difference": float(hi_d["mean"].iloc[0] - lo_d["mean"].iloc[0]),
        })
    return df, pd.DataFrame(contrasts)


def spline_models(ars: pd.DataFrame) -> pd.DataFrame:
    """Natural-cubic-spline regression with controls and pitcher-clustered SEs."""
    d = ars.dropna(subset=["uniq_pct", "release_speed", "zone_pct",
                           "platoon_share", "usage_share"]).copy()
    d["velo_z"] = d.groupby(["family", "game_year"])["release_speed"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=1))
    d["year_f"] = d["game_year"].astype(str)
    rows = []
    for col in ["whiff_pct_eb", "csw_pct_eb", "rv100_eb", "xwobacon_eb"]:
        sub = d.dropna(subset=[col])
        if len(sub) < 200:
            continue
        formula = (f"{col} ~ cr(uniq_pct, df=4) + velo_z + zone_pct "
                   "+ platoon_share + usage_share + C(family) + C(year_f)")
        try:
            m = smf.ols(formula, data=sub).fit(
                cov_type="cluster", cov_kwds={"groups": sub["pitcher"]})
        except Exception as exc:  # pragma: no cover - defensive
            print(f"  spline model failed for {col}: {exc}")
            continue
        # predicted effect of moving from the 10th to the 90th uniqueness pct
        grid = sub.iloc[[0]].copy()
        preds = {}
        for q in (0.1, 0.9):
            g = grid.copy()
            g["uniq_pct"] = q
            for c in ["velo_z", "zone_pct", "platoon_share", "usage_share"]:
                g[c] = sub[c].mean()
            preds[q] = float(m.predict(g).iloc[0])
        # joint test that every spline coefficient on uniqueness is zero
        spline_terms = [t for t in m.params.index if t.startswith("cr(")]
        p_joint = float("nan")
        if spline_terms:
            try:
                p_joint = float(m.wald_test(
                    [f"{t} = 0" for t in spline_terms], scalar=True
                ).pvalue)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"  joint spline test failed for {col}: {exc}")
        rows.append({
            "outcome": col.replace("_eb", ""), "n": int(len(sub)),
            "effect_p10_to_p90": preds[0.9] - preds[0.1],
            "p_joint_spline": p_joint,
            "r2": float(m.rsquared),
            "n_spline_terms": len(spline_terms),
        })
    return pd.DataFrame(rows)


def within_between_models(ars: pd.DataFrame) -> pd.DataFrame:
    """Separate "this pitch got weirder" from "weird pitchers are better".

    Two estimators on the same panel of pitcher-pitches observed in at least
    two seasons:

    * **within** — pitcher-by-family fixed effects absorbed by demeaning, so
      the coefficient comes only from a given pitcher's own pitch moving in and
      out of the league norm across seasons. This is the causal-flavoured one:
      pitcher talent is held constant by construction.
    * **between** — one row per pitcher-pitch, regressing career-average
      outcome on career-average uniqueness. This captures selection: whether
      the pitchers who own unusual pitches are simply better.

    A mixed model was tried first and proved numerically fragile: outcome
    variances here span five orders of magnitude (whiff% around 80, xwOBAcon
    around 0.0015) and three of four outcomes failed with singular matrices.
    Demeaning gives the identical within estimand without the fit.
    """
    d = ars.dropna(subset=["uniq_pct"]).copy()
    d["velo_z"] = d.groupby(["family", "game_year"])["release_speed"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=1))
    grp = d.groupby(["pitcher", "family"])["uniq_pct"]
    d["uniq_between"] = grp.transform("mean")
    d["n_seasons"] = grp.transform("size")
    d["unit"] = (d["pitcher"].astype(str) + "|" + d["family"].astype(str))

    controls = ["velo_z", "zone_pct", "platoon_share"]
    rows = []
    for col in ["whiff_pct_eb", "csw_pct_eb", "rv100_eb", "xwobacon_eb"]:
        sub = d.dropna(subset=[col] + controls)
        sub = sub[sub["n_seasons"] >= 2]
        if len(sub) < 300:
            continue

        # ---- within: absorb pitcher-by-family effects -------------------
        ydum = pd.get_dummies(sub["game_year"].astype(str), prefix="yr",
                              drop_first=True, dtype=float)
        X = pd.concat([sub[["uniq_pct"] + controls].astype(float), ydum], axis=1)
        y = sub[col].astype(float)
        unit = sub["unit"].to_numpy()
        Xw = X - X.groupby(unit).transform("mean")
        yw = y - y.groupby(unit).transform("mean")
        keep = Xw.std() > 1e-12
        Xw = Xw.loc[:, keep]
        mw = sm.OLS(yw, sm.add_constant(Xw, has_constant="add")).fit(
            cov_type="cluster", cov_kwds={"groups": sub["pitcher"]})

        # ---- between: one row per pitcher-pitch --------------------------
        agg = (sub.groupby(["unit", "family"])
               .agg(**{col: (col, "mean"), "uniq": ("uniq_between", "first"),
                       **{c: (c, "mean") for c in controls},
                       "pitcher": ("pitcher", "first")})
               .reset_index())
        fdum = pd.get_dummies(agg["family"], prefix="fam", drop_first=True,
                              dtype=float)
        Xb = pd.concat([agg[["uniq"] + controls].astype(float), fdum], axis=1)
        mb = sm.OLS(agg[col].astype(float),
                    sm.add_constant(Xb, has_constant="add")).fit(
            cov_type="cluster", cov_kwds={"groups": agg["pitcher"]})

        rows.append({
            "outcome": col.replace("_eb", ""),
            "n_within": int(len(sub)), "n_units": int(sub["unit"].nunique()),
            "within_coef": float(mw.params.get("uniq_pct", np.nan)),
            "within_se": float(mw.bse.get("uniq_pct", np.nan)),
            "within_p": float(mw.pvalues.get("uniq_pct", np.nan)),
            "between_coef": float(mb.params.get("uniq", np.nan)),
            "between_se": float(mb.bse.get("uniq", np.nan)),
            "between_p": float(mb.pvalues.get("uniq", np.nan)),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["within_sig_fdr"] = S.bh_fdr(df["within_p"].to_numpy(), config.FDR_Q)
    return df


def gbm_incremental(ars: pd.DataFrame, years: list[int],
                    max_rows: int = 1_200_000) -> tuple[pd.DataFrame, dict]:
    """Does uniqueness add whiff-prediction signal beyond the raw pitch features?

    Both models see velocity, movement, release geometry, location and count;
    only one also sees the pitch's uniqueness percentile. Grouped by pitcher so
    the held-out fold contains unseen pitchers.
    """
    frames = []
    for year in years:
        path = config.PARQUET_DIR / "pitches" / f"game_year={year}"
        if not path.exists():
            continue
        d = pd.read_parquet(path, columns=[
            "pitcher", "family", "game_year", "release_speed", "ivb", "hb_arm",
            "release_spin_rate", "release_extension", "release_pos_z",
            "release_side_arm", "plate_x", "plate_z", "balls", "strikes",
            "stand", "p_throws", "is_swing", "is_whiff",
        ])
        frames.append(d[d["is_swing"]])
        del d
    if not frames:
        return pd.DataFrame(), {}
    sw = pd.concat(frames, ignore_index=True)
    del frames

    key = ars[["pitcher", "family", "game_year", "uniq_pct"]]
    sw = sw.merge(key, on=["pitcher", "family", "game_year"], how="inner")
    sw = sw.dropna(subset=["uniq_pct", "release_speed", "ivb", "hb_arm",
                           "plate_x", "plate_z"])
    if len(sw) > max_rows:
        sw = sw.sample(max_rows, random_state=config.SEED)

    sw["platoon"] = (sw["stand"] != sw["p_throws"]).astype(int)
    sw["fam_code"] = sw["family"].astype("category").cat.codes
    base_feats = ["release_speed", "ivb", "hb_arm", "release_spin_rate",
                  "release_extension", "release_pos_z", "release_side_arm",
                  "plate_x", "plate_z", "balls", "strikes", "platoon", "fam_code"]
    y = sw["is_whiff"].astype(int).to_numpy()
    groups = sw["pitcher"].to_numpy()

    results = []
    gkf = GroupKFold(n_splits=4)
    for label, feats in (("without_uniqueness", base_feats),
                         ("with_uniqueness", base_feats + ["uniq_pct"])):
        X = sw[feats].to_numpy(float)
        lls, aucs = [], []
        for tr, te in gkf.split(X, y, groups):
            clf = HistGradientBoostingClassifier(
                max_iter=180, learning_rate=0.08, max_depth=6,
                random_state=config.SEED,
            ).fit(X[tr], y[tr])
            p = clf.predict_proba(X[te])[:, 1]
            lls.append(log_loss(y[te], p))
            aucs.append(roc_auc_score(y[te], p))
        results.append({"model": label, "n": int(len(sw)),
                        "log_loss": float(np.mean(lls)),
                        "auc": float(np.mean(aucs))})

    res = pd.DataFrame(results)
    delta = {
        "delta_log_loss": float(res.loc[1, "log_loss"] - res.loc[0, "log_loss"]),
        "delta_auc": float(res.loc[1, "auc"] - res.loc[0, "auc"]),
    }

    # partial dependence of whiff probability on uniqueness
    Xf = sw[base_feats + ["uniq_pct"]].to_numpy(float)
    clf = HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.08, max_depth=6, random_state=config.SEED
    ).fit(Xf, y)
    pd_res = partial_dependence(clf, Xf, features=[len(base_feats)],
                                grid_resolution=25, kind="average")
    pdp = pd.DataFrame({
        "uniq_pct": pd_res["grid_values"][0],
        "whiff_prob": pd_res["average"][0],
    })
    return res, {"delta": delta, "pdp": pdp}


def figure_gradient(dec: pd.DataFrame, pdp: pd.DataFrame | None) -> None:
    """fig10 - the headline uniqueness gradient."""
    outcomes = ["whiff_pct", "csw_pct", "rv100", "xwobacon"]
    present = [o for o in outcomes if o in set(dec["outcome"])]
    n = len(present) + (1 if pdp is not None and not pdp.empty else 0)
    fig, axes = P.facet_grid(n, ncols=min(n, 3), width=3.7, height=3.0)
    for ax, out in zip(axes, present):
        g = dec[dec["outcome"] == out].sort_values("decile")
        color = P.SERIES[0] if oc.OUTCOME_SIGN[out] > 0 else P.SERIES[1]
        P.band(ax, g["decile"], g["lo"], g["hi"], color)
        ax.plot(g["decile"], g["mean"], color=color, marker="o", markersize=5,
                markeredgecolor=P.SURFACE, markeredgewidth=1.0)
        P.style_axis(ax, title=oc.OUTCOME_LABELS[out],
                     xlabel="Uniqueness decile (10 = most unusual)")
        ax.set_xticks(range(1, 11))
        better = "higher is better" if oc.OUTCOME_SIGN[out] > 0 else "lower is better"
        ax.annotate(better, xy=(0.03, 0.94), xycoords="axes fraction",
                    fontsize=8, color=P.INK_MUTED, va="top")
    if pdp is not None and not pdp.empty:
        ax = axes[len(present)]
        ax.plot(pdp["uniq_pct"], 100 * pdp["whiff_prob"], color=P.SERIES[2])
        P.style_axis(ax, title="Model-adjusted whiff probability",
                     xlabel="Uniqueness percentile",
                     ylabel="Whiff% per swing (partial dependence)")
    P.suptitle(fig, "Do unusual pitches perform better?",
               "Pitcher-season pitches grouped by how far their shape sits from "
               "the same-season league norm; bands are 95% bootstrap intervals")
    P.finish(fig)
    P.save(fig, "fig10_uniqueness_gradient")


def main() -> None:
    manifest = json.loads((config.RESULTS_DIR / "data_manifest.json").read_text())
    feats = manifest["shape_features"]
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

    arsenal = pd.read_parquet(D.arsenal_path())
    years = sorted(arsenal["game_year"].unique())

    scored = U.score_arsenal(arsenal, feats)
    scored = add_shrunk_outcomes(scored)
    scored.to_parquet(config.PARQUET_DIR / "arsenal_scored.parquet", index=False)
    D.save_result(
        scored[["pitcher", "player_name", "family", "game_year", "pitches",
                "uniq_maha", "uniq_knn", "uniq_pct", "uniq_decile",
                "whiff_pct_eb", "csw_pct_eb", "rv100_eb", "xwobacon_eb"]]
        .sort_values("uniq_pct", ascending=False).head(60).round(4),
        "s5_most_unusual_pitches",
    )

    dec, contrasts = decile_gradient(scored, reps)
    D.save_result(dec, "s5_decile_gradient")
    D.save_result(contrasts, "s5_decile_contrasts")
    print("=== top vs bottom uniqueness decile ===")
    print(contrasts.round(4).to_string(index=False))

    sp = spline_models(scored)
    if not sp.empty:
        D.save_result(sp, "s5_spline_models")
        print("\n=== spline regression: 10th → 90th uniqueness percentile ===")
        print(sp.round(4).to_string(index=False))

    mm = within_between_models(scored)
    if not mm.empty:
        D.save_result(mm, "s5_within_between")
        print("\n=== within-pitcher vs between-pitcher ===")
        print(mm.round(4).to_string(index=False))

    gbm, extra = gbm_incremental(scored, years)
    pdp = None
    if not gbm.empty:
        D.save_result(gbm, "s5_gbm_incremental")
        pdp = extra["pdp"]
        D.save_result(pdp, "s5_gbm_pdp")
        print("\n=== gradient boosting: does uniqueness add signal? ===")
        print(gbm.round(5).to_string(index=False))
        print(extra["delta"])

    figure_gradient(dec, pdp)
    D.write_meta("s5_outlier", {
        "years": years, "features": feats, "bootstrap_reps": reps,
        "arsenal_rows_scored": int(len(scored)),
        "gbm_delta": extra.get("delta") if extra else None,
    })


if __name__ == "__main__":
    main()
