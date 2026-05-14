import numpy as np
import pandas as pd

from webapp.hitter.calculations import classify_barrel


def compute_bip_stats(bip_df: pd.DataFrame) -> pd.DataFrame:
    if bip_df.empty:
        return pd.DataFrame()

    bip_df = bip_df.copy()
    bip_df["is_line_drive"] = (bip_df["launch_angle"] >= 10) & (bip_df["launch_angle"] <= 25)
    bip_df["is_barrel"] = classify_barrel(bip_df["launch_speed"], bip_df["launch_angle"])
    bip_df["is_hard_hit"] = bip_df["launch_speed"] >= 95
    bip_df["is_bbia_100"] = (
        (bip_df["launch_speed"] >= 100)
        & (bip_df["launch_angle"] >= 15)
        & (bip_df["launch_angle"] <= 50)
    )

    grouped = bip_df.groupby("pitcher")

    stats = pd.DataFrame({
        "player_name": grouped["player_name"].first(),
        "bip": grouped.size(),
        "ld_pct": (grouped["is_line_drive"].sum() / grouped.size() * 100).round(1),
        "barrel_pct": (grouped["is_barrel"].sum() / grouped.size() * 100).round(1),
        "hh_pct": (grouped["is_hard_hit"].sum() / grouped.size() * 100).round(1),
        "bbia_100": grouped["is_bbia_100"].sum().astype(int),
    })

    return stats.reset_index()


def compute_pa_stats(pa_df: pd.DataFrame) -> pd.DataFrame:
    if pa_df.empty:
        return pd.DataFrame()

    pa_df = pa_df.copy()
    pa_df["k_bb_pct"] = ((pa_df["k_count"] - pa_df["bb_count"]) / pa_df["pa"] * 100).round(1)
    pa_df["strike_pct"] = (pa_df["strikes_total"] / pa_df["total_pitches"] * 100).round(1)
    pa_df["whiffs"] = pa_df["whiffs"].astype(int)
    pa_df["csw_pct"] = (
        (pa_df["called_strikes"] + pa_df["whiffs"]) / pa_df["total_pitches"] * 100
    ).round(1)

    return pa_df[[
        "pitcher", "player_name", "total_pitches", "pa",
        "k_bb_pct", "strike_pct", "whiffs", "csw_pct",
    ]]


def compute_fb_velo(fb_df: pd.DataFrame) -> pd.DataFrame:
    if fb_df.empty:
        return pd.DataFrame(columns=["pitcher", "fb_velo"])
    return fb_df[["pitcher", "fb_velo"]].copy()


def compute_leaderboard(
    bip_tf: pd.DataFrame,
    pa_tf: pd.DataFrame,
    fb_tf: pd.DataFrame,
    bip_l14: pd.DataFrame,
    pa_l14: pd.DataFrame,
    fb_l14: pd.DataFrame,
    min_bip: int = 0,
) -> list[dict]:
    tf_bip = compute_bip_stats(bip_tf)
    tf_pa = compute_pa_stats(pa_tf)
    tf_fb = compute_fb_velo(fb_tf)

    if tf_bip.empty:
        return []

    tf = tf_bip.merge(tf_pa, on="pitcher", how="left", suffixes=("", "_pa"))
    if "player_name_pa" in tf.columns:
        tf["player_name"] = tf["player_name"].fillna(tf["player_name_pa"])
    tf = tf.merge(tf_fb, on="pitcher", how="left")

    tf = tf[tf["bip"] >= min_bip]

    # L14
    l14_bip = compute_bip_stats(bip_l14)
    l14_pa = compute_pa_stats(pa_l14)
    l14_fb = compute_fb_velo(fb_l14)

    if not l14_bip.empty:
        l14 = l14_bip.merge(l14_pa, on="pitcher", how="left", suffixes=("", "_pa"))
        l14 = l14.merge(l14_fb, on="pitcher", how="left")
        l14_cols = {
            "bip": "l14_bip", "ld_pct": "l14_ld_pct", "barrel_pct": "l14_barrel_pct",
            "hh_pct": "l14_hh_pct", "bbia_100": "l14_bbia_100",
            "k_bb_pct": "l14_k_bb_pct", "strike_pct": "l14_strike_pct",
            "csw_pct": "l14_csw_pct", "fb_velo": "l14_fb_velo",
        }
        # whiffs from PA merge may be 'whiffs' or 'whiffs_y' depending on merge
        for whiff_col in ("whiffs_y", "whiffs"):
            if whiff_col in l14.columns and whiff_col not in l14_cols:
                l14_cols[whiff_col] = "l14_whiffs"
                break
        l14 = l14.rename(columns=l14_cols)
        merge_cols = ["pitcher"] + [c for c in l14_cols.values() if c in l14.columns]
        tf = tf.merge(l14[merge_cols], on="pitcher", how="left")
    else:
        for col in ["l14_bip", "l14_ld_pct", "l14_barrel_pct", "l14_hh_pct",
                     "l14_bbia_100", "l14_k_bb_pct", "l14_strike_pct",
                     "l14_whiffs", "l14_csw_pct", "l14_fb_velo"]:
            tf[col] = None

    tf = tf.sort_values("fb_velo", ascending=False)
    tf = tf.round({"fb_velo": 1})
    tf = tf.where(pd.notna(tf), None)

    return tf.to_dict(orient="records")
