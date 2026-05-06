import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import click

from savant import __version__
from savant.audit import (
    find_duplicates,
    find_gaps,
    get_status,
    verify_date,
    verify_row_counts,
)
from savant.config import get_db_path, get_log_dir, get_log_level
from savant.db import (
    get_fetch_log,
    get_pitch_count_for_date,
    init_db,
    insert_pitches,
    upsert_fetch_log,
)
from savant.fetch import GAME_TYPES, FetchError, fetch_date, rate_limit_pause

GAME_TYPE_CHOICES = click.Choice(list(GAME_TYPES.keys()))


def setup_logging(verbose: bool) -> None:
    level = "DEBUG" if verbose else get_log_level()
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers = [logging.StreamHandler(sys.stdout)]

    log_file = log_dir / "statcast.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


@click.group()
@click.version_option(__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """MLB Statcast data pipeline - fetch and manage pitch-by-pitch data."""
    setup_logging(verbose)


@cli.command()
def init() -> None:
    """Initialize the database with schema."""
    db_path = get_db_path()
    click.echo(f"Initializing database at {db_path}")
    init_db()
    click.echo("Database initialized successfully.")


@cli.command()
@click.option(
    "--start-date",
    default="2025-02-20",
    help="Start date for backfill (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    default=None,
    help="End date for backfill (defaults to yesterday)",
)
@click.option(
    "--game-types",
    default="SRFDLW",
    help="Game types to fetch (e.g. SRFDLW)",
)
def backfill(start_date: str, end_date: Optional[str], game_types: str) -> None:
    """Backfill historical data from Baseball Savant."""
    init_db()

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1)

    types = list(game_types)
    click.echo(f"Backfilling {start} to {end}, game types: {','.join(types)}")

    current = start
    total_rows = 0
    skipped = 0
    errors = 0

    try:
        from tqdm import tqdm

        total_days = (end - start).days + 1
        pbar = tqdm(total=total_days, desc="Backfilling", unit="day")
    except ImportError:
        pbar = None

    while current <= end:
        date_str = current.isoformat()

        already_fetched = True
        for gt in types:
            log = get_fetch_log(date_str, gt)
            if not log or log["fetch_status"] != "success":
                already_fetched = False
                break

        if already_fetched:
            skipped += 1
            if pbar:
                pbar.update(1)
            else:
                click.echo(f"  {date_str}: already fetched, skipping")
            current += timedelta(days=1)
            continue

        try:
            start_time = time.time()
            df = fetch_date(date_str, types)
            elapsed = time.time() - start_time

            if df.empty:
                for gt in types:
                    upsert_fetch_log(date_str, gt, 0, "empty", elapsed)
                if pbar:
                    pbar.update(1)
                else:
                    click.echo(f"  {date_str}: no data (empty day)")
            else:
                inserted = insert_pitches(df)
                total_rows += inserted

                for gt in types:
                    gt_count = len(df[df["game_type"] == gt]) if "game_type" in df.columns else len(df)
                    upsert_fetch_log(
                        date_str, gt, gt_count, "success", elapsed
                    )

                if pbar:
                    pbar.set_postfix(rows=total_rows, refresh=False)
                    pbar.update(1)
                else:
                    click.echo(f"  {date_str}: {inserted} rows inserted")

            rate_limit_pause()

        except (FetchError, Exception) as e:
            errors += 1
            logging.getLogger(__name__).error("Error fetching %s: %s", date_str, e)
            for gt in types:
                upsert_fetch_log(date_str, gt, 0, "failed", 0, str(e))
            if pbar:
                pbar.update(1)
            else:
                click.echo(f"  {date_str}: ERROR - {e}")

        current += timedelta(days=1)

    if pbar:
        pbar.close()

    click.echo(f"\nBackfill complete: {total_rows} rows inserted, {skipped} days skipped, {errors} errors")


@cli.command()
@click.option("--date", "target_date", default=None, help="Specific date (YYYY-MM-DD)")
@click.option("--days-back", default=1, help="Number of days back from today")
@click.option("--game-types", default="SRFDLW", help="Game types to fetch")
def update(
    target_date: Optional[str], days_back: int, game_types: str
) -> None:
    """Fetch data for recent dates (cron-friendly)."""
    init_db()

    types = list(game_types)

    if target_date:
        dates = [date.fromisoformat(target_date)]
    else:
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(days_back, 0, -1)]

    total_rows = 0

    for d in dates:
        date_str = d.isoformat()

        already_fetched = True
        for gt in types:
            log = get_fetch_log(date_str, gt)
            if not log or log["fetch_status"] != "success":
                already_fetched = False
                break

        if already_fetched:
            click.echo(f"{date_str}: already up to date, skipping")
            continue

        try:
            start_time = time.time()
            df = fetch_date(date_str, types)
            elapsed = time.time() - start_time

            if df.empty:
                for gt in types:
                    upsert_fetch_log(date_str, gt, 0, "empty", elapsed)
                click.echo(f"{date_str}: no data (no games or offseason)")
            else:
                inserted = insert_pitches(df)
                total_rows += inserted

                for gt in types:
                    gt_count = len(df[df["game_type"] == gt]) if "game_type" in df.columns else len(df)
                    upsert_fetch_log(date_str, gt, gt_count, "success", elapsed)

                click.echo(f"{date_str}: {inserted} rows inserted")

            rate_limit_pause()

        except FetchError as e:
            click.echo(f"{date_str}: ERROR - {e}", err=True)
            for gt in types:
                upsert_fetch_log(date_str, gt, 0, "failed", 0, str(e))

    click.echo(f"Update complete: {total_rows} total rows inserted")


@cli.command()
@click.option("--season", default=None, type=int, help="Season year to audit")
@click.option("--fix", is_flag=True, help="Automatically re-fetch missing/failed dates")
def audit(season: Optional[int], fix: bool) -> None:
    """Audit database integrity - find gaps, duplicates, and mismatches."""
    issues_found = False

    click.echo("=== Row Count Verification ===")
    mismatches = verify_row_counts()
    if mismatches:
        issues_found = True
        click.echo(f"Found {len(mismatches)} row count mismatches:")
        for m in mismatches:
            click.echo(
                f"  {m['game_date']} ({m['game_type']}): logged={m['logged']}, actual={m['actual']}"
            )
    else:
        click.echo("All row counts match.")

    click.echo("\n=== Duplicate Check ===")
    dups = find_duplicates()
    if dups:
        issues_found = True
        click.echo(f"Found {len(dups)} duplicate pitch records!")
    else:
        click.echo("No duplicates found.")

    seasons_to_check = [season] if season else [2025, 2026]

    click.echo("\n=== Gap Detection ===")
    for yr in seasons_to_check:
        gaps = find_gaps(yr)
        if gaps:
            issues_found = True
            for g in gaps:
                click.echo(
                    f"  {g['season']}: {g['count']} missing dates"
                )
                for d in g["missing_dates"][:10]:
                    click.echo(f"    - {d}")
                if g["count"] > 10:
                    click.echo(f"    ... and {g['count'] - 10} more")
        else:
            click.echo(f"  {yr}: no gaps found")

    if fix and issues_found:
        click.echo("\n=== Fixing Issues ===")
        for yr in seasons_to_check:
            gaps = find_gaps(yr)
            for g in gaps:
                for d in g["missing_dates"]:
                    try:
                        df = fetch_date(d, list(GAME_TYPES.keys()))
                        if not df.empty:
                            inserted = insert_pitches(df)
                            click.echo(f"  Fixed {d}: {inserted} rows inserted")
                        rate_limit_pause()
                    except FetchError as e:
                        click.echo(f"  Failed to fix {d}: {e}")

    if not issues_found:
        click.echo("\nAudit passed - no issues found.")


@cli.command("status")
def status_cmd() -> None:
    """Show database status and statistics."""
    db_path = get_db_path()

    if not db_path.exists():
        click.echo("Database not found. Run 'statcast init' first.")
        return

    info = get_status()

    if info["date_range"]["min"]:
        click.echo(f"Date range: {info['date_range']['min']} to {info['date_range']['max']}")
    else:
        click.echo("Database is empty.")
        return

    click.echo(f"Total rows: {info['total_rows']:,}")
    click.echo(f"Last fetch: {info['last_fetch']}")

    click.echo("\nRows by season and game type:")
    for row in info["by_season"]:
        click.echo(f"  {row['game_year']} {row['game_type']}: {row['cnt']:,}")

    click.echo("\nFetch log summary:")
    for row in info["fetch_log_summary"]:
        click.echo(f"  {row['fetch_status']}: {row['cnt']}")

    db_size = db_path.stat().st_size
    if db_size > 1_000_000_000:
        click.echo(f"\nDatabase size: {db_size / 1_000_000_000:.1f} GB")
    elif db_size > 1_000_000:
        click.echo(f"\nDatabase size: {db_size / 1_000_000:.1f} MB")
    else:
        click.echo(f"\nDatabase size: {db_size / 1_000:.1f} KB")


@cli.command()
@click.argument("target_date", required=False)
def verify(target_date: Optional[str]) -> None:
    """Verify data integrity for a specific date."""
    if not target_date:
        db_path = get_db_path()
        if not db_path.exists():
            click.echo("Database not found.")
            return

        from savant.db import get_connection
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT MAX(game_date) as max_date FROM statcast_pitches"
            ).fetchone()
            target_date = row["max_date"]
            if not target_date:
                click.echo("Database is empty.")
                return
        finally:
            conn.close()

    click.echo(f"Verifying {target_date}...")
    result = verify_date(target_date)

    click.echo(f"Total rows: {result.get('total_rows', 0)}")

    if result["errors"]:
        click.echo("ERRORS:")
        for e in result["errors"]:
            click.echo(f"  - {e}")
    if result["warnings"]:
        click.echo("WARNINGS:")
        for w in result["warnings"]:
            click.echo(f"  - {w}")

    if not result["errors"] and not result["warnings"]:
        click.echo("All checks passed.")


if __name__ == "__main__":
    cli()
