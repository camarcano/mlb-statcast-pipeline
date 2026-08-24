"""Bring the Statcast database current before projecting.

This reuses the pipeline's own fetch and insert functions rather than shelling
out to its CLI. The one behavioural difference from ``statcast update`` is
``force_days``: the most recent days are re-fetched even when ``fetch_log`` says
they succeeded, because a day first pulled while games were in progress is
logged as a success while still being incomplete. Re-fetching is safe - the
``(game_pk, at_bat_number, pitch_number)`` unique constraint plus
``INSERT OR IGNORE`` makes inserts idempotent.
"""

import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional, Sequence

from savant.db import get_fetch_log, init_db, insert_pitches, upsert_fetch_log
from savant.fetch import FetchError, fetch_date, rate_limit_pause

logger = logging.getLogger(__name__)


def refresh_statcast(
    db_path: Path,
    end_date: str,
    days_back: int = 7,
    force_days: int = 2,
    game_types: Sequence[str] = ("R",),
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """Fetch the last `days_back` days up to `end_date` into the Statcast DB.

    Days already logged as successful are skipped unless they fall inside the
    trailing `force_days` window. Returns a summary dict.
    """
    init_db(db_path)
    types = list(game_types)

    end = date.fromisoformat(end_date)
    start = end - timedelta(days=days_back - 1)
    force_from = end - timedelta(days=force_days - 1) if force_days > 0 else None

    inserted_total = 0
    fetched: list[str] = []
    skipped: list[str] = []
    failed: dict[str, str] = {}

    current = start
    while current <= end:
        date_str = current.isoformat()
        forced = force_from is not None and current >= force_from

        if not forced and _all_logged_success(date_str, types, db_path):
            skipped.append(date_str)
            current += timedelta(days=1)
            continue

        try:
            started = time.time()
            df = fetch_date(date_str, types)
            elapsed = time.time() - started

            if df.empty:
                for gt in types:
                    upsert_fetch_log(date_str, gt, 0, "empty", elapsed, db_path=db_path)
            else:
                inserted = insert_pitches(df, db_path=db_path)
                inserted_total += inserted
                for gt in types:
                    gt_rows = int((df["game_type"] == gt).sum()) if "game_type" in df else len(df)
                    upsert_fetch_log(date_str, gt, gt_rows, "success", elapsed, db_path=db_path)
                if on_progress:
                    on_progress(f"  {date_str}: +{inserted} rows")

            fetched.append(date_str)
            rate_limit_pause()

        except (FetchError, Exception) as exc:  # noqa: BLE001 - one bad day must not abort the run
            failed[date_str] = str(exc)
            logger.warning("Refresh failed for %s: %s", date_str, exc)
            for gt in types:
                upsert_fetch_log(date_str, gt, 0, "failed", 0, str(exc), db_path=db_path)
            if on_progress:
                on_progress(f"  {date_str}: FAILED - {exc}")

        current += timedelta(days=1)

    return {
        "inserted": inserted_total,
        "fetched": fetched,
        "skipped": skipped,
        "failed": failed,
    }


def _all_logged_success(date_str: str, types: Sequence[str], db_path: Path) -> bool:
    for gt in types:
        log = get_fetch_log(date_str, gt, db_path=db_path)
        if not log or log["fetch_status"] not in ("success", "empty"):
            return False
    return True
