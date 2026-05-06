import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from savant.db import get_connection, get_pitch_count_for_date

logger = logging.getLogger(__name__)

VALID_GAME_TYPES = {"S", "R", "F", "D", "L", "W"}


def get_season_date_ranges(season_year: int) -> dict[str, tuple[date, date]]:
    spring_start = date(season_year, 2, 20)
    regular_start = date(season_year, 3, 25)
    regular_end = date(season_year, 10, 5)
    post_end = date(season_year, 11, 5)

    return {
        "S": (spring_start, regular_start - timedelta(days=1)),
        "R": (regular_start, regular_end),
        "post": (regular_end + timedelta(days=1), post_end),
    }


def find_gaps(
    season_year: int,
    db_path: Optional[Path] = None,
) -> list[dict]:
    conn = get_connection(db_path)
    try:
        ranges = get_season_date_ranges(season_year)
        gaps = []

        fetched_dates = conn.execute(
            "SELECT DISTINCT game_date FROM fetch_log WHERE fetch_status = 'success' AND game_date >= ? AND game_date < ?",
            (
                ranges["S"][0].isoformat(),
                ranges["post"][1].isoformat(),
            ),
        ).fetchall()
        fetched_set = {row["game_date"] for row in fetched_dates}

        all_dates = set()
        for label, (start, end) in ranges.items():
            if label == "post":
                game_types = ["F", "D", "L", "W"]
            else:
                game_types = [label]

            current = start
            while current <= end:
                all_dates.add(current.isoformat())
                current += timedelta(days=1)

        today = date.today().isoformat()
        missing = sorted(d for d in all_dates if d < today and d not in fetched_set)

        if missing:
            gaps.append(
                {
                    "season": season_year,
                    "missing_dates": missing,
                    "count": len(missing),
                }
            )

        return gaps
    finally:
        conn.close()


def find_duplicates(db_path: Optional[Path] = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT game_pk, at_bat_number, pitch_number, COUNT(*) as cnt
               FROM statcast_pitches
               GROUP BY game_pk, at_bat_number, pitch_number
               HAVING cnt > 1"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def verify_row_counts(db_path: Optional[Path] = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        mismatches = conn.execute(
            """SELECT fl.game_date, fl.game_type, fl.row_count AS logged,
                      COUNT(sp.id) AS actual
               FROM fetch_log fl
               LEFT JOIN statcast_pitches sp
                   ON sp.game_date = fl.game_date AND sp.game_type = fl.game_type
               WHERE fl.fetch_status = 'success'
               GROUP BY fl.game_date, fl.game_type, fl.row_count
               HAVING logged != actual"""
        ).fetchall()
        return [dict(r) for r in mismatches]
    finally:
        conn.close()


def verify_date(
    game_date: str, db_path: Optional[Path] = None
) -> dict:
    conn = get_connection(db_path)
    try:
        result = {
            "date": game_date,
            "errors": [],
            "warnings": [],
        }

        total = conn.execute(
            "SELECT COUNT(*) FROM statcast_pitches WHERE game_date = ?",
            (game_date,),
        ).fetchone()[0]

        if total == 0:
            result["errors"].append("No rows found for this date")
            return result

        result["total_rows"] = total

        log_entries = conn.execute(
            "SELECT * FROM fetch_log WHERE game_date = ?", (game_date,)
        ).fetchall()

        for entry in log_entries:
            entry_dict = dict(entry)
            logged = entry_dict["row_count"]
            actual = get_pitch_count_for_date(game_date, entry_dict["game_type"], db_path)
            if logged != actual:
                result["errors"].append(
                    f"Row count mismatch for game_type={entry_dict['game_type']}: "
                    f"logged={logged}, actual={actual}"
                )

        null_required = conn.execute(
            """SELECT COUNT(*) FROM statcast_pitches
               WHERE game_date = ?
               AND (game_pk IS NULL OR batter IS NULL OR pitcher IS NULL
                    OR at_bat_number IS NULL OR pitch_number IS NULL)""",
            (game_date,),
        ).fetchone()[0]

        if null_required > 0:
            result["errors"].append(
                f"{null_required} rows have NULL in required fields"
            )

        invalid_types = conn.execute(
            """SELECT DISTINCT game_type FROM statcast_pitches
               WHERE game_date = ? AND game_type NOT IN ('S','R','F','D','L','W')""",
            (game_date,),
        ).fetchall()

        if invalid_types:
            result["warnings"].append(
                f"Invalid game_type values: {[r['game_type'] for r in invalid_types]}"
            )

        sanity_failures = conn.execute(
            """SELECT COUNT(*) FROM statcast_pitches
               WHERE game_date = ?
               AND (balls NOT BETWEEN 0 AND 3
                    OR strikes NOT BETWEEN 0 AND 2
                    OR outs_when_up NOT BETWEEN 0 AND 2
                    OR inning < 1)""",
            (game_date,),
        ).fetchone()[0]

        if sanity_failures > 0:
            result["warnings"].append(
                f"{sanity_failures} rows have out-of-range count values"
            )

        return result
    finally:
        conn.close()


def get_status(db_path: Optional[Path] = None) -> dict:
    conn = get_connection(db_path)
    try:
        status = {}

        date_range = conn.execute(
            "SELECT MIN(game_date) as min_date, MAX(game_date) as max_date FROM statcast_pitches"
        ).fetchone()
        status["date_range"] = {
            "min": date_range["min_date"],
            "max": date_range["max_date"],
        }

        total = conn.execute("SELECT COUNT(*) FROM statcast_pitches").fetchone()[0]
        status["total_rows"] = total

        by_season = conn.execute(
            """SELECT game_year, game_type, COUNT(*) as cnt
               FROM statcast_pitches
               GROUP BY game_year, game_type
               ORDER BY game_year, game_type"""
        ).fetchall()
        status["by_season"] = [dict(r) for r in by_season]

        log_status = conn.execute(
            """SELECT fetch_status, COUNT(*) as cnt
               FROM fetch_log
               GROUP BY fetch_status"""
        ).fetchall()
        status["fetch_log_summary"] = [dict(r) for r in log_status]

        last_fetch = conn.execute(
            "SELECT MAX(last_fetch_ts) as last_ts FROM fetch_log"
        ).fetchone()
        status["last_fetch"] = last_fetch["last_ts"]

        return status
    finally:
        conn.close()
