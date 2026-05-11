import numpy as np
import pandas as pd


def classify_barrel(ev: pd.Series, la: pd.Series) -> pd.Series:
    ev = ev.fillna(0)
    la = la.fillna(0)

    is_barrel = (
        (ev >= 97.5)
        & (
            ((la >= 25.5) & (la <= 30.5))
            | ((la < 25.5) & ((25.5 - la) < (ev - 97.5)))
            | ((la > 30.5) & (((la - 30.5) * 2) < ((ev - 97.5) * 3)))
        )
    )
    return is_barrel


def trimmed_mean(series: pd.Series, trim_pct: float = 0.1) -> float:
    vals = series.dropna()
    if len(vals) < 5:
        return vals.mean() if len(vals) > 0 else np.nan
    cutoff = int(np.ceil(len(vals) * trim_pct))
    if cutoff >= len(vals):
        return vals.mean()
    return vals.nlargest(len(vals) - cutoff).mean()


def compute_bip_stats(bip_df: pd.DataFrame) -> pd.DataFrame:
    if bip_df.empty:
        return pd.DataFrame()

    bip_df = bip_df.copy()
    bip_df["is_barrel"] = classify_barrel(bip_df["launch_speed"], bip_df["launch_angle"])
    bip_df["is_100plus"] = bip_df["launch_speed"] >= 100
    bip_df["is_bbia_100"] = (
        (bip_df["launch_speed"] >= 100)
        & (bip_df["launch_angle"] >= 15)
        & (bip_df["launch_angle"] <= 50)
    )

    grouped = bip_df.groupby("batter")

    stats = pd.DataFrame({
        "player_name": grouped["player_name"].first(),
        "bip": grouped.size(),
        "ev": grouped["launch_speed"].mean(),
        "max_ev": grouped["launch_speed"].max(),
        "av_la": grouped["launch_angle"].mean(),
        "ev90": grouped["launch_speed"].quantile(0.9),
        "barrels": grouped["is_barrel"].sum().astype(int),
        "bip_100": grouped["is_100plus"].sum().astype(int),
        "bbia_100": grouped["is_bbia_100"].sum().astype(int),
        "bat_speed": grouped["bat_speed"].apply(trimmed_mean),
    })

    stats["barrel_pct"] = (stats["barrels"] / stats["bip"] * 100).round(1)

    stats = stats.reset_index()

    return stats


def compute_pa_stats(pa_df: pd.DataFrame) -> pd.DataFrame:
    if pa_df.empty:
        return pd.DataFrame()

    pa_df = pa_df.copy()
    pa_df["k_pct"] = (pa_df["k_count"] / pa_df["pa"] * 100).round(1)

    ab = pa_df["pa"] - pa_df["non_ab"]
    ab = ab.replace(0, np.nan)
    pa_df["xba"] = (pa_df["xba_num"] / ab).round(3)

    denom = pa_df["woba_denom_total"].replace(0, np.nan)
    pa_df["xwoba"] = ((pa_df["xwoba_bip"] + pa_df["xwoba_nonbip"]) / denom).round(3)

    return pa_df[["batter", "player_name", "pa", "k_pct", "xba", "xwoba"]]


def compute_leaderboard(
    bip_tf: pd.DataFrame,
    pa_tf: pd.DataFrame,
    bip_l14: pd.DataFrame,
    pa_l14: pd.DataFrame,
    min_bip: int = 10,
) -> list[dict]:
    tf_bip = compute_bip_stats(bip_tf)
    tf_pa = compute_pa_stats(pa_tf)

    if tf_bip.empty:
        return []

    tf = tf_bip.merge(tf_pa, on="batter", how="left", suffixes=("", "_pa"))
    if "player_name_pa" in tf.columns:
        tf["player_name"] = tf["player_name"].fillna(tf["player_name_pa"])

    tf = tf[tf["bip"] >= min_bip]

    l14_bip = compute_bip_stats(bip_l14)
    l14_pa = compute_pa_stats(pa_l14)

    if not l14_bip.empty:
        l14 = l14_bip.merge(l14_pa, on="batter", how="left", suffixes=("", "_pa"))
        l14_cols = {
            "bip": "l14_bip",
            "ev": "l14_ev",
            "max_ev": "l14_max_ev",
            "av_la": "l14_av_la",
            "ev90": "l14_ev90",
            "barrels": "l14_barrels",
            "barrel_pct": "l14_barrel_pct",
            "bat_speed": "l14_bat_speed",
            "bip_100": "l14_bip_100",
            "bbia_100": "l14_bbia_100",
            "pa": "l14_pa",
            "k_pct": "l14_k_pct",
            "xba": "l14_xba",
            "xwoba": "l14_xwoba",
        }
        l14 = l14.rename(columns=l14_cols)
        tf = tf.merge(
            l14[["batter"] + list(l14_cols.values())],
            on="batter",
            how="left",
        )
    else:
        l14_suffixes = [
            "l14_bip", "l14_ev", "l14_max_ev", "l14_av_la", "l14_ev90",
            "l14_barrels", "l14_barrel_pct", "l14_bat_speed", "l14_bip_100",
            "l14_bbia_100", "l14_pa", "l14_k_pct", "l14_xba", "l14_xwoba",
        ]
        for col in l14_suffixes:
            tf[col] = None

    tf = tf.sort_values("ev", ascending=False)
    tf = tf.round({"ev": 1, "max_ev": 1, "av_la": 1, "ev90": 1, "bat_speed": 1})

    return tf.to_dict(orient="records")
