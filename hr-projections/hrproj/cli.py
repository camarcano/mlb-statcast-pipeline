"""Command line entry point."""

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import click
import pandas as pd

from hrproj import __version__, schedule as schedule_mod
from hrproj.backtest import run_backtest, sweep
from hrproj.config import (
    DEFAULT_PARAMS,
    GAMES_PER_SEASON,
    ModelParams,
    default_as_of,
    get_cache_db,
    get_out_dir,
    get_season,
    get_statcast_db,
    season_end_date,
    season_start_date,
)
from hrproj.data import latest_game_date, load_pa_frame, team_games_played
from hrproj.model import build_projection
from hrproj.refresh import refresh_statcast
from hrproj.report import to_console, write_outputs
from hrproj.simulate import simulate
from hrproj.teams import fangraphs


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise click.ClickException(
            f"Statcast database not found at {db_path}.\n"
            "Point HRPROJ_STATCAST_DB at your pipeline database, or create one with:\n"
            "  statcast backfill --start-date 2026-03-25 --game-types R"
        )
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _params_from_options(
    sims: int, seed: int, no_park: bool, no_opponent: bool,
    half_life: Optional[float], phi: Optional[float], k_pa: Optional[float],
) -> ModelParams:
    params = DEFAULT_PARAMS.replace(
        sims=sims, seed=seed, use_park=not no_park, use_opponent=not no_opponent
    )
    overrides = {}
    if half_life is not None:
        overrides["half_life_days"] = half_life
    if phi is not None:
        overrides["phi"] = phi
    if k_pa is not None:
        overrides["k_pa"] = k_pa
    return params.replace(**overrides) if overrides else params


def _resolve_as_of(conn: sqlite3.Connection, season: int, as_of: Optional[str]) -> str:
    if as_of:
        return as_of
    latest = latest_game_date(conn, season)
    wanted = default_as_of()
    if latest and latest < wanted:
        click.echo(
            f"Note: latest game in the database is {latest} (expected {wanted}); "
            "projecting as of the latest available date.",
            err=True,
        )
        return latest
    return wanted


def _load_pa(conn: sqlite3.Connection, season: int, as_of: str) -> pd.DataFrame:
    pa = load_pa_frame(conn, season, season_start_date(season), as_of)
    if pa.empty:
        raise click.ClickException(
            f"No {season} regular-season plate appearances found through {as_of}."
        )
    return pa


def _remaining_games(
    pa: pd.DataFrame, season: int, as_of: str, use_schedule: bool, timeout: int
) -> tuple[list[dict], str]:
    """Remaining matchups plus a label describing where they came from."""
    start = (pd.Timestamp(as_of) + pd.Timedelta(days=1)).date().isoformat()
    end = season_end_date(season)
    cache_db = get_cache_db()

    if use_schedule:
        try:
            schedule_mod.refresh_cache(cache_db, start, end, season, timeout)
        except Exception as exc:  # noqa: BLE001 - fall through to cache, then to the stub
            click.echo(f"Schedule fetch failed ({exc}); using cached schedule.", err=True)

        # Projecting from a past date: games played since then were still ahead
        # of that vantage point, so they belong in the remaining set.
        include_completed = start <= pd.Timestamp.today().date().isoformat()
        remaining = schedule_mod.load_remaining(
            cache_db, season, start, end, include_completed=include_completed
        )
        if remaining:
            return remaining, "statsapi"
        click.echo("No cached schedule available; falling back to 162 - games played.", err=True)

    played = team_games_played(pa).to_dict()
    return (
        schedule_mod.fallback_remaining(played, GAMES_PER_SEASON),
        f"{GAMES_PER_SEASON}-minus-games-played",
    )


@click.group()
@click.version_option(__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """Rest-of-season team home run projections from Statcast data."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


@cli.command()
@click.option("--as-of", default=None, help="Project as of this date (default: yesterday)")
@click.option("--season", default=None, type=int, help="Season to project")
@click.option("--sims", default=DEFAULT_PARAMS.sims, help="Monte Carlo iterations")
@click.option("--seed", default=DEFAULT_PARAMS.seed, help="Random seed")
@click.option("--refresh/--no-refresh", default=True, help="Fetch recent Statcast data first")
@click.option("--refresh-days", default=7, help="Days back to refresh")
@click.option("--force-days", default=2, help="Trailing days to re-fetch even if logged complete")
@click.option("--schedule/--no-schedule", default=True, help="Use the MLB StatsAPI schedule")
@click.option("--no-park", is_flag=True, help="Ignore park home run factors")
@click.option("--no-opponent", is_flag=True, help="Ignore opposing staff quality")
@click.option("--half-life", default=None, type=float, help="Override recency half-life (days)")
@click.option("--phi", default=None, type=float, help="Override xHR weight in the blend")
@click.option("--k-pa", default=None, type=float, help="Override regression strength (PA)")
@click.option("--top", default=30, help="Rows to print")
@click.option("--format", "formats", default="", help="Also write files: json,csv,html")
def project(
    as_of, season, sims, seed, refresh, refresh_days, force_days, schedule,
    no_park, no_opponent, half_life, phi, k_pa, top, formats,
) -> None:
    """Project final home run totals for all 30 teams."""
    season = season or get_season()
    db_path = get_statcast_db()

    if refresh:
        click.echo(f"Refreshing Statcast data in {db_path} ...", err=True)
        summary = refresh_statcast(
            db_path,
            end_date=as_of or default_as_of(),
            days_back=refresh_days,
            force_days=force_days,
            on_progress=lambda msg: click.echo(msg, err=True),
        )
        click.echo(
            f"  {summary['inserted']:,} rows inserted, "
            f"{len(summary['skipped'])} days already complete, "
            f"{len(summary['failed'])} failed.",
            err=True,
        )

    conn = _connect(db_path)
    try:
        resolved_as_of = _resolve_as_of(conn, season, as_of)
        pa = _load_pa(conn, season, resolved_as_of)
    finally:
        conn.close()

    remaining, source = _remaining_games(pa, season, resolved_as_of, schedule, timeout=30)
    params = _params_from_options(sims, seed, no_park, no_opponent, half_life, phi, k_pa)

    projection = build_projection(pa, remaining, resolved_as_of, season, params, source)
    result = simulate(projection)

    click.echo(to_console(projection, result, top))

    wanted = tuple(f.strip() for f in formats.split(",") if f.strip())
    if wanted:
        written = write_outputs(projection, result, get_out_dir(), wanted)
        for path in written:
            click.echo(f"Wrote {path}", err=True)


@cli.command()
@click.argument("team")
@click.option("--as-of", default=None, help="As-of date (default: yesterday)")
@click.option("--season", default=None, type=int)
@click.option("--top", default=15, help="Hitters to show")
@click.option("--no-park", is_flag=True)
@click.option("--no-opponent", is_flag=True)
def players(team, as_of, season, top, no_park, no_opponent) -> None:
    """Show the hitters driving one team's projection."""
    season = season or get_season()
    conn = _connect(get_statcast_db())
    try:
        resolved_as_of = _resolve_as_of(conn, season, as_of)
        pa = _load_pa(conn, season, resolved_as_of)
    finally:
        conn.close()

    team = team.upper()
    reverse = {fangraphs(t): t for t in pa["bat_team"].unique()}
    team = reverse.get(team, team)

    remaining, source = _remaining_games(pa, season, resolved_as_of, True, timeout=30)
    params = _params_from_options(
        DEFAULT_PARAMS.sims, DEFAULT_PARAMS.seed, no_park, no_opponent, None, None, None
    )
    projection = build_projection(pa, remaining, resolved_as_of, season, params, source)

    if team not in projection.teams:
        raise click.ClickException(f"Unknown team '{team}'.")

    ti = projection.teams[team]
    df = ti.batters.copy()
    df["proj_pa"] = df["share"] * ti.pa_per_game * ti.games_remaining
    df["proj_hr"] = df["proj_pa"] * df["rate"] * (
        ti.context_sum / max(ti.games_remaining, 1)
    )
    df = df.sort_values("proj_hr", ascending=False).head(top)

    click.echo(
        f"{fangraphs(team)} - {ti.hr_to_date} HR in {ti.games_played} games, "
        f"{ti.games_remaining} to play, {ti.expected_remaining:.1f} expected "
        f"(projected {ti.projected:.1f})"
    )
    click.echo(f"{'Hitter':<24}{'PA':>6}{'HR':>5}{'xHR':>7}{'HR/PA':>8}{'RoS PA':>8}{'RoS HR':>8}")
    click.echo("-" * 66)
    for _, r in df.iterrows():
        name = (r["player_name"] or "unknown")[:23]
        click.echo(
            f"{name:<24}{r['pa']:>6.0f}{r['hr']:>5.0f}{r['xhr']:>7.1f}"
            f"{r['rate']:>8.4f}{r['proj_pa']:>8.1f}{r['proj_hr']:>8.1f}"
        )


@cli.command()
@click.option("--cutoff", required=True, help="Fit using data through this date")
@click.option("--end", default=None, help="Score against games through this date")
@click.option("--season", default=None, type=int)
@click.option("--sweep", "do_sweep", is_flag=True, help="Grid-search the rate constants")
@click.option("--no-park", is_flag=True)
@click.option("--no-opponent", is_flag=True)
def backtest(cutoff, end, season, do_sweep, no_park, no_opponent) -> None:
    """Score the model out of sample against simpler alternatives."""
    season = season or get_season()
    conn = _connect(get_statcast_db())
    try:
        resolved_end = _resolve_as_of(conn, season, end)
        pa = _load_pa(conn, season, resolved_end)
    finally:
        conn.close()

    params = _params_from_options(
        DEFAULT_PARAMS.sims, DEFAULT_PARAMS.seed, no_park, no_opponent, None, None, None
    )

    if do_sweep:
        table = sweep(pa, cutoff, resolved_end, season, params)
        click.echo(f"Parameter sweep, fit through {cutoff}, scored through {resolved_end}")
        click.echo(table.head(15).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        best = table.iloc[0]
        click.echo(
            f"\nBest: half_life={best['half_life']:.0f} phi={best['phi']:.2f} "
            f"k_pa={best['k_pa']:.0f} (MAE {best['mae']:.2f})"
        )
        return

    result = run_backtest(pa, cutoff, resolved_end, season, params)
    click.echo(f"Backtest: fit through {cutoff}, scored on games through {resolved_end}")
    click.echo(
        f"{result.per_team['games'].sum()} team-games, "
        f"{result.per_team['actual'].sum():.0f} home runs hit\n"
    )
    click.echo(result.scores.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    worst = result.per_team.assign(err=lambda d: (d["model"] - d["actual"]).abs())
    worst = worst.sort_values("err", ascending=False).head(5)
    click.echo("\nLargest model misses:")
    for _, r in worst.iterrows():
        click.echo(
            f"  {fangraphs(r['team']):<4} actual {r['actual']:>5.0f}  "
            f"model {r['model']:>6.1f}  ({r['model'] - r['actual']:+.1f})"
        )


@cli.command("schedule-refresh")
@click.option("--season", default=None, type=int)
@click.option("--from-date", default=None, help="Start date (default: today)")
def schedule_refresh(season, from_date) -> None:
    """Refresh the cached remaining schedule from the MLB StatsAPI."""
    season = season or get_season()
    start = from_date or pd.Timestamp.today().date().isoformat()
    end = season_end_date(season)
    count = schedule_mod.refresh_cache(get_cache_db(), start, end, season)
    click.echo(f"Cached {count} games ({start} to {end}) in {get_cache_db()}")


if __name__ == "__main__":
    cli()
