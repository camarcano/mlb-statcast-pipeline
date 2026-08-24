"""Runtime configuration and model constants.

Model constants live in :class:`ModelParams` so the backtest sweep can vary them
without touching module-level state.
"""

import os
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Regular season bounds (MLB StatsAPI).
SEASON_OPENING = {2026: "2026-03-25"}
SEASON_END = {2026: "2026-09-27"}
GAMES_PER_SEASON = 162


def get_season() -> int:
    return int(os.getenv("HRPROJ_SEASON", "2026"))


def get_statcast_db() -> Path:
    """Path to the pipeline's Statcast database (read/refreshed, never schema-changed)."""
    raw = os.getenv("HRPROJ_STATCAST_DB")
    if raw:
        return Path(raw).expanduser().resolve()
    from savant.config import get_db_path

    return get_db_path()


def get_cache_db() -> Path:
    """Path to this tool's own database (schedule cache). Separate from the Statcast DB."""
    raw = os.getenv("HRPROJ_CACHE_DB", "data/hrproj.db")
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def get_out_dir() -> Path:
    raw = os.getenv("HRPROJ_OUT_DIR", "out")
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def season_end_date(season: Optional[int] = None) -> str:
    season = season or get_season()
    return SEASON_END.get(season, f"{season}-10-05")


def season_start_date(season: Optional[int] = None) -> str:
    """Lower bound for data queries - deliberately loose, unlike opening day."""
    season = season or get_season()
    return f"{season}-01-01"


def season_opening_date(season: Optional[int] = None) -> str:
    """Opening day, for a first backfill."""
    season = season or get_season()
    return SEASON_OPENING.get(season, f"{season}-03-20")


@dataclass(frozen=True)
class ModelParams:
    """Tunable model constants. Defaults are the backtest-selected values."""

    # Per-batter HR rate estimation. These three are the backtest sweep's picks
    # (see README); differences among the top handful of settings are inside the
    # noise of a 30-team holdout.
    half_life_days: float = 75.0   # recency decay on plate appearances
    phi: float = 1.0               # weight on xHR vs actual HR in the blend
    k_pa: float = 400.0            # regression-to-league strength, in weighted PA

    # Playing time
    pt_half_life_days: float = 14.0
    pt_window_days: int = 28
    pt_active_days: int = 10       # no PA in this many days => assumed unavailable
    share_cap_mult: float = 1.15   # max share of team PA, as a multiple of 1/9
    team_pa_k_games: float = 30.0  # shrink team PA/game toward league

    # Context factors
    park_n0: float = 1200.0        # air-BBE shrinkage constant for park factors
    opp_n0: float = 1500.0         # air-BBE shrinkage constant for opposing staffs
    use_park: bool = True
    use_opponent: bool = True
    league_normalize: bool = True  # rescale so the league aggregate matches the league rate

    # xHR grid
    ev_bin: float = 1.0
    la_bin: float = 1.0
    ev_sigma: float = 1.5
    la_sigma: float = 2.5
    spray_min_n: float = 400.0     # per-cell weight below which spray detail is pooled away

    # Simulation
    sims: int = 10000
    seed: int = 20260824
    # Season-to-season the league home run environment drifts with the weather -
    # 2026 ran from .0280 in April to .0343 in June and back to .0293 in August.
    # No model anchored on past data forecasts that, so it enters the simulation
    # as a multiplicative factor shared by all 30 clubs: it widens every interval
    # without moving the odds of one team out-homering another. Set to 0 to drop it.
    league_env_sd: float = 0.07
    # Round-number seasons worth reporting the odds of.
    hr_milestones: tuple = (40, 50)

    def replace(self, **kwargs) -> "ModelParams":
        return replace(self, **kwargs)


DEFAULT_PARAMS = ModelParams()


def default_as_of() -> str:
    """Default as-of date: yesterday, since today's games may still be in progress."""
    return (date.today() - timedelta(days=1)).isoformat()
