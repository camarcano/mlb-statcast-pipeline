"""Loading and shaping Statcast plate-appearance data.

One query does the work: every plate-appearance-ending pitch in the season, with
the batted-ball measurements attached. Batted balls are a subset of those rows
(``type = 'X'``), so team totals, expected-HR inputs, park factors and opposing
staff rates all derive from a single frame.
"""

import sqlite3
from typing import Optional

import numpy as np
import pandas as pd

from hrproj.teams import BATTING_TEAM_SQL, NON_PA_EVENTS

# Statcast's hit-coordinate origin (home plate) in the scoreboard coordinate system.
HC_X_HOME = 125.42
HC_Y_HOME = 198.27

# Batted balls in this launch-angle band are the ones parks and pitching staffs
# can plausibly turn into (or deny) home runs.
AIR_LA_MIN = 10.0
AIR_LA_MAX = 50.0

PA_QUERY = f"""
SELECT
    batter,
    player_name,
    stand,
    game_date,
    game_pk,
    at_bat_number,
    inning_topbot,
    home_team,
    away_team,
    {BATTING_TEAM_SQL} AS bat_team,
    events,
    type,
    launch_speed,
    launch_angle,
    hc_x,
    hc_y
FROM statcast_pitches
WHERE events IS NOT NULL
  AND game_type = 'R'
  AND game_year = ?
  AND game_date BETWEEN ? AND ?
"""


def spray_angle(hc_x: pd.Series, hc_y: pd.Series, stand: pd.Series) -> pd.Series:
    """Pull-relative spray angle in degrees: positive is pulled, negative is oppo.

    The raw angle is positive toward right field; a right-handed batter pulls to
    left, so the sign is flipped for right-handed hitters.
    """
    x = pd.to_numeric(hc_x, errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(hc_y, errors="coerce").to_numpy(dtype=float)
    raw = np.degrees(np.arctan2(x - HC_X_HOME, HC_Y_HOME - y))
    return pd.Series(np.where(stand == "R", -raw, raw), index=hc_x.index)


def load_pa_frame(
    conn: sqlite3.Connection,
    season: int,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Every plate appearance in the window, with derived team/contact columns."""
    df = pd.read_sql_query(PA_QUERY, conn, params=(season, start_date, end_date))
    if df.empty:
        return df

    df = df[~df["events"].isin(NON_PA_EVENTS)].copy()

    # SQLite hands back object dtype for columns that are entirely NULL.
    for col in ("launch_speed", "launch_angle", "hc_x", "hc_y"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["pitch_team"] = np.where(
        df["bat_team"] == df["home_team"], df["away_team"], df["home_team"]
    )
    df["venue"] = df["home_team"]
    df["is_hr"] = (df["events"] == "home_run").astype(float)
    df["is_bbe"] = (df["type"] == "X") & (df["launch_speed"] > 0) & df["launch_angle"].notna()
    df["is_air"] = (
        df["is_bbe"]
        & df["launch_angle"].between(AIR_LA_MIN, AIR_LA_MAX)
    )
    df["spray"] = spray_angle(df["hc_x"], df["hc_y"], df["stand"])
    df["game_date"] = pd.to_datetime(df["game_date"])

    return df


def decay_weights(game_dates: pd.Series, as_of: str, half_life_days: float) -> pd.Series:
    """Exponential recency weights: 1.0 on the as-of date, halving every `half_life`."""
    days = (pd.Timestamp(as_of) - game_dates).dt.days.clip(lower=0)
    return pd.Series(0.5 ** (days / half_life_days), index=game_dates.index)


def team_games_played(pa: pd.DataFrame) -> pd.Series:
    """Games played per team, counting each club's own appearances in a game_pk."""
    if pa.empty:
        return pd.Series(dtype=int)
    return pa.groupby("bat_team")["game_pk"].nunique()


def team_hr_to_date(pa: pd.DataFrame) -> pd.Series:
    if pa.empty:
        return pd.Series(dtype=int)
    return pa.groupby("bat_team")["is_hr"].sum().astype(int)


def team_pa_to_date(pa: pd.DataFrame) -> pd.Series:
    if pa.empty:
        return pd.Series(dtype=int)
    return pa.groupby("bat_team").size()


def latest_game_date(conn: sqlite3.Connection, season: int) -> Optional[str]:
    row = conn.execute(
        "SELECT MAX(game_date) FROM statcast_pitches WHERE game_type = 'R' AND game_year = ?",
        (season,),
    ).fetchone()
    return row[0] if row and row[0] else None
