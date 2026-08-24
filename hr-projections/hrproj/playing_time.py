"""How many plate appearances each hitter gets in the games that remain.

Shares come from recent usage rather than a depth chart: a hitter who stopped
appearing three weeks ago has decayed to nothing, and a call-up enters at the
rate they are actually being used. The cap keeps a hot streak from projecting a
physically impossible workload.
"""

import numpy as np
import pandas as pd

from hrproj.config import ModelParams
from hrproj.data import decay_weights

LINEUP_SLOTS = 9

# Bounds on the Dirichlet concentration used for roster-churn noise in simulation.
MIN_CONCENTRATION = 200.0
MAX_CONCENTRATION = 2000.0


def team_pa_per_game(pa: pd.DataFrame, params: ModelParams) -> pd.Series:
    """Team PA per game, shrunk toward the league rate."""
    if pa.empty:
        return pd.Series(dtype=float)

    team_pa = pa.groupby("bat_team").size()
    team_games = pa.groupby("bat_team")["game_pk"].nunique()
    league_rate = float(team_pa.sum() / team_games.sum())

    k = params.team_pa_k_games
    return (team_pa + k * league_rate) / (team_games + k)


def cap_shares(shares: np.ndarray, cap: float) -> np.ndarray:
    """Cap each share at `cap`, redistributing the excess over the uncapped ones."""
    shares = np.asarray(shares, dtype=float)
    if shares.sum() <= 0:
        return shares
    shares = shares / shares.sum()
    if cap * len(shares) <= 1.0:  # cap cannot be satisfied; leave proportional
        return shares

    for _ in range(100):
        over = shares > cap + 1e-12
        if not over.any():
            break
        excess = float((shares[over] - cap).sum())
        shares[over] = cap
        free = ~over
        free_total = float(shares[free].sum())
        if free_total <= 0:
            shares[free] = excess / max(1, free.sum())
            break
        shares[free] += excess * shares[free] / free_total
    return shares


def batter_shares(
    pa: pd.DataFrame, as_of: str, params: ModelParams
) -> pd.DataFrame:
    """Per-team share of plate appearances for each active hitter.

    Columns: team, batter, share, w_pa, concentration.
    """
    if pa.empty:
        return pd.DataFrame(columns=["team", "batter", "share", "w_pa", "concentration"])

    as_of_ts = pd.Timestamp(as_of)
    window_start = as_of_ts - pd.Timedelta(days=params.pt_window_days - 1)
    recent = pa[pa["game_date"] >= window_start].copy()
    if recent.empty:
        recent = pa.copy()

    recent["w"] = decay_weights(recent["game_date"], as_of, params.pt_half_life_days)

    grouped = recent.groupby(["bat_team", "batter"])
    agg = grouped.agg(w_pa=("w", "sum"), last_game=("game_date", "max")).reset_index()

    active_cutoff = as_of_ts - pd.Timedelta(days=params.pt_active_days)

    cap = params.share_cap_mult / LINEUP_SLOTS
    rows = []
    for team, team_agg in agg.groupby("bat_team"):
        grp = team_agg[team_agg["last_game"] >= active_cutoff]
        if grp.empty:
            # The whole club is stale (a data gap, or an off-week at the cutoff).
            # Better to project its known hitters than to drop the team.
            grp = team_agg
        shares = cap_shares(grp["w_pa"].to_numpy(), cap)
        concentration = float(
            np.clip(grp["w_pa"].sum(), MIN_CONCENTRATION, MAX_CONCENTRATION)
        )
        for (_, r), s in zip(grp.iterrows(), shares):
            rows.append({
                "team": team,
                "batter": r["batter"],
                "share": float(s),
                "w_pa": float(r["w_pa"]),
                "concentration": concentration,
            })

    return pd.DataFrame(rows)
