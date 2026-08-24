"""Remaining-schedule retrieval from the MLB StatsAPI, with a local cache.

The cache lives in this tool's own SQLite file; the Statcast database is never
written to by this module. When the API is unreachable and the cache is empty,
callers fall back to `162 - games played` with neutral parks.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

import requests

from hrproj.teams import STATSAPI_TEAM_IDS

logger = logging.getLogger(__name__)

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
TEAMS_URL = "https://statsapi.mlb.com/api/v1/teams"
USER_AGENT = "mlb-hr-projections/0.1.0"

# Games that have already been played.
COMPLETED_STATES = frozenset({"Final", "Game Over", "Completed Early"})

# Games that will not be played as scheduled. A postponed game reappears with a
# new date and gamePk once rescheduled, so counting the original would
# double-count it; a suspended game likewise resumes and settles as Final.
ABANDONED_STATES = frozenset({
    "Cancelled", "Canceled", "Postponed", "Suspended", "Forfeit",
})

DEAD_STATES = COMPLETED_STATES | ABANDONED_STATES

CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS schedule_games (
    game_pk INTEGER PRIMARY KEY,
    game_date TEXT NOT NULL,
    season INTEGER NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    venue_id INTEGER,
    venue_name TEXT,
    status TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule_games(season, game_date);

CREATE TABLE IF NOT EXISTS team_venues (
    team TEXT NOT NULL,
    season INTEGER NOT NULL,
    venue_id INTEGER,
    venue_name TEXT,
    PRIMARY KEY (team, season)
);
"""


def cache_connection(cache_db: Path) -> sqlite3.Connection:
    cache_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(cache_db))
    conn.row_factory = sqlite3.Row
    conn.executescript(CACHE_SCHEMA)
    conn.commit()
    return conn


def _get_json(url: str, params: dict, timeout: int) -> dict:
    resp = requests.get(
        url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    return resp.json()


def fetch_schedule(
    start_date: str, end_date: str, season: int, timeout: int = 30
) -> list[dict]:
    """Fetch regular-season games in the window from the StatsAPI."""
    payload = _get_json(
        SCHEDULE_URL,
        {
            "sportId": 1,
            "gameType": "R",
            "startDate": start_date,
            "endDate": end_date,
            "season": season,
        },
        timeout,
    )

    games: list[dict] = []
    for day in payload.get("dates", []):
        for game in day.get("games", []):
            home_id = game["teams"]["home"]["team"]["id"]
            away_id = game["teams"]["away"]["team"]["id"]
            home = STATSAPI_TEAM_IDS.get(home_id)
            away = STATSAPI_TEAM_IDS.get(away_id)
            if not home or not away:
                logger.warning("Unknown team id in game %s", game.get("gamePk"))
                continue
            venue = game.get("venue") or {}
            games.append({
                "game_pk": game["gamePk"],
                "game_date": day["date"],
                "season": season,
                "home_team": home,
                "away_team": away,
                "venue_id": venue.get("id"),
                "venue_name": venue.get("name"),
                "status": (game.get("status") or {}).get("detailedState", ""),
            })
    return games


def fetch_team_venues(season: int, timeout: int = 30) -> list[dict]:
    """Each club's home venue, used to spot neutral-site games."""
    payload = _get_json(
        TEAMS_URL, {"sportId": 1, "season": season}, timeout
    )
    rows = []
    for team in payload.get("teams", []):
        abbr = STATSAPI_TEAM_IDS.get(team.get("id"))
        if not abbr:
            continue
        venue = team.get("venue") or {}
        rows.append({
            "team": abbr,
            "season": season,
            "venue_id": venue.get("id"),
            "venue_name": venue.get("name"),
        })
    return rows


def refresh_cache(
    cache_db: Path, start_date: str, end_date: str, season: int, timeout: int = 30
) -> int:
    """Refresh the cached schedule for the window. Returns the number of games stored."""
    games = fetch_schedule(start_date, end_date, season, timeout)
    venues = fetch_team_venues(season, timeout)

    conn = cache_connection(cache_db)
    try:
        conn.execute(
            "DELETE FROM schedule_games WHERE season = ? AND game_date BETWEEN ? AND ?",
            (season, start_date, end_date),
        )
        conn.executemany(
            """INSERT OR REPLACE INTO schedule_games
               (game_pk, game_date, season, home_team, away_team, venue_id, venue_name, status)
               VALUES (:game_pk, :game_date, :season, :home_team, :away_team,
                       :venue_id, :venue_name, :status)""",
            games,
        )
        conn.executemany(
            """INSERT OR REPLACE INTO team_venues (team, season, venue_id, venue_name)
               VALUES (:team, :season, :venue_id, :venue_name)""",
            venues,
        )
        conn.commit()
    finally:
        conn.close()

    return len(games)


def load_remaining(
    cache_db: Path,
    season: int,
    start_date: str,
    end_date: str,
    include_completed: bool = False,
) -> list[dict]:
    """Cached games in the window that are still to be played.

    Each game is returned twice - once per club - as ``{team, opponent, game_date,
    home, venue_team}``, where ``venue_team`` is the club whose park factor
    applies, or ``None`` at a neutral site.

    ``include_completed`` keeps games that have already finished, which is what a
    projection run with a past ``as-of`` date needs: from that vantage point those
    games were still ahead. Abandoned games are dropped either way.
    """
    conn = cache_connection(cache_db)
    try:
        rows = conn.execute(
            """SELECT * FROM schedule_games
               WHERE season = ? AND game_date BETWEEN ? AND ?
               ORDER BY game_date""",
            (season, start_date, end_date),
        ).fetchall()
        venue_map = {
            r["venue_id"]: r["team"]
            for r in conn.execute(
                "SELECT team, venue_id FROM team_venues WHERE season = ?", (season,)
            ).fetchall()
        }
    finally:
        conn.close()

    skip = ABANDONED_STATES if include_completed else DEAD_STATES

    matchups: list[dict] = []
    for row in rows:
        if row["status"] in skip:
            continue
        venue_team = venue_map.get(row["venue_id"])
        if venue_team is not None and venue_team != row["home_team"]:
            venue_team = None  # neutral site: the home club is not in its own park
        for team, opponent, is_home in (
            (row["home_team"], row["away_team"], True),
            (row["away_team"], row["home_team"], False),
        ):
            matchups.append({
                "game_pk": row["game_pk"],
                "game_date": row["game_date"],
                "team": team,
                "opponent": opponent,
                "home": is_home,
                "venue_team": venue_team,
            })
    return matchups


def fallback_remaining(
    games_played: "dict[str, int] | Iterable[tuple[str, int]]",
    games_per_season: int = 162,
) -> list[dict]:
    """Schedule-free fallback: `games_per_season - games played`, neutral parks.

    Opponents are unknown, so each stub game carries ``opponent=None`` and
    ``venue_team=None``, which the model reads as neutral context.
    """
    if not isinstance(games_played, dict):
        games_played = dict(games_played)

    stubs: list[dict] = []
    for team, played in games_played.items():
        for _ in range(max(0, games_per_season - int(played))):
            stubs.append({
                "game_pk": None,
                "game_date": None,
                "team": team,
                "opponent": None,
                "home": None,
                "venue_team": None,
            })
    return stubs


def last_refreshed(cache_db: Path, season: int) -> Optional[str]:
    conn = cache_connection(cache_db)
    try:
        row = conn.execute(
            "SELECT MAX(fetched_at) FROM schedule_games WHERE season = ?", (season,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()
