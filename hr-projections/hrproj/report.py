"""Rendering projections for a terminal, a spreadsheet, or a browser."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from hrproj.model import Projection
from hrproj.simulate import SimulationResult
from hrproj.teams import fangraphs

COLUMNS = [
    ("Tm", "team_fg", 4, "{}"),
    ("HR", "hr_to_date", 4, "{:.0f}"),
    ("G-", "games_remaining", 3, "{:.0f}"),
    ("Rest", "expected_remaining", 5, "{:.1f}"),
    ("Proj", "projected", 6, "{:.1f}"),
    ("p10", "p10", 5, "{:.0f}"),
    ("p90", "p90", 5, "{:.0f}"),
    ("Lead%", "p_lead", 6, "{:.1%}"),
    ("Top3%", "p_top3", 6, "{:.1%}"),
    ("Rk", "current_rank", 3, "{:.0f}"),
]


def _decorate(totals: pd.DataFrame) -> pd.DataFrame:
    df = totals.copy()
    df["team_fg"] = df["team"].map(fangraphs)
    return df


def to_console(projection: Projection, result: SimulationResult, top: int = 30) -> str:
    df = _decorate(result.totals).head(top)

    header = "  ".join(name.rjust(width) for name, _, width, _ in COLUMNS)
    lines = [
        f"Team home run projections - {projection.season} regular season",
        f"As of {projection.as_of} | {result.sims:,} simulations | "
        f"schedule: {projection.schedule_source}",
        "",
        header,
        "-" * len(header),
    ]

    for _, row in df.iterrows():
        cells = []
        for _, key, width, fmt in COLUMNS:
            value = row[key]
            cells.append(fmt.format(value).rjust(width))
        lines.append("  ".join(cells))

    leader = df.iloc[0]
    lines += [
        "",
        f"Favourite: {leader['team_fg']} at {leader['projected']:.1f} projected "
        f"({leader['p_lead']:.1%} to lead MLB)",
        "HR = home runs to date, G- = games remaining, Rest = expected home runs "
        "in those games,",
        "p10/p90 = 10th/90th percentile of the simulated final total, "
        "Rk = current rank.",
    ]

    for warning in projection.warnings:
        lines.append(f"WARNING: {warning}")

    return "\n".join(lines)


PLAYER_COLUMNS = [
    ("Hitter", "player_name", 22, "{}"),
    ("Tm", "team_fg", 4, "{}"),
    ("PA", "pa", 5, "{:.0f}"),
    ("HR", "hr_to_date", 4, "{:.0f}"),
    ("xHR", "xhr", 6, "{:.1f}"),
    ("RoS", "expected_remaining", 5, "{:.1f}"),
    ("Proj", "projected", 6, "{:.1f}"),
    ("p10", "p10", 4, "{:.0f}"),
    ("p90", "p90", 4, "{:.0f}"),
]


def players_to_console(
    projection: Projection,
    result: SimulationResult,
    top: int = 25,
    milestones: tuple = (40, 50),
) -> str:
    """Leaderboard of projected individual home run totals."""
    if result.players.empty:
        return "No player projections available."

    df = result.players.copy()
    df["team_fg"] = df["team"].map(fangraphs)
    df = df.head(top)

    columns = list(PLAYER_COLUMNS)
    for milestone in milestones:
        key = f"p_{milestone}"
        if key in df.columns:
            columns.append((f"{milestone}+", key, 6, "{:.1%}"))

    header = "  ".join(
        name.ljust(width) if key == "player_name" else name.rjust(width)
        for name, key, width, _ in columns
    )
    lines = [
        f"Projected individual home run totals - {projection.season}",
        f"As of {projection.as_of} | {result.sims:,} simulations",
        "",
        header,
        "-" * len(header),
    ]

    for _, row in df.iterrows():
        cells = []
        for _, key, width, fmt in columns:
            text = fmt.format(row[key])
            cells.append(text[:width].ljust(width) if key == "player_name" else text.rjust(width))
        lines.append("  ".join(cells))

    for milestone in milestones:
        key = f"p_{milestone}"
        if key not in result.players.columns:
            continue
        contenders = result.players[result.players[key] >= 0.01]
        expected = result.players[key].sum()
        lines.append(
            f"\n{len(contenders)} hitters have at least a 1% chance of {milestone}+ "
            f"home runs; {expected:.1f} are expected to get there."
        )

    return "\n".join(lines)


def write_player_outputs(
    projection: Projection,
    result: SimulationResult,
    out_dir: Path,
    formats: tuple[str, ...] = ("csv",),
) -> list[Path]:
    if result.players.empty:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    df = result.players.copy()
    df["team_fg"] = df["team"].map(fangraphs)
    written: list[Path] = []

    if "csv" in formats:
        path = out_dir / f"hr_players_{projection.as_of}.csv"
        df.to_csv(path, index=False)
        written.append(path)

    if "json" in formats:
        path = out_dir / f"hr_players_{projection.as_of}.json"
        path.write_text(json.dumps({
            "as_of": projection.as_of,
            "season": projection.season,
            "sims": result.sims,
            "players": df.to_dict(orient="records"),
        }, indent=2, default=str))
        written.append(path)

    if "html" in formats:
        path = out_dir / f"hr_players_{projection.as_of}.html"
        path.write_text(_players_html(projection, result, df))
        written.append(path)

    return written


def _players_html(projection: Projection, result: SimulationResult, df: pd.DataFrame) -> str:
    milestone_cols = [c for c in df.columns if c.startswith("p_")]
    display = df[[
        "player_name", "team_fg", "pa", "hr_to_date", "xhr",
        "expected_remaining", "projected", "p10", "p90", *milestone_cols,
    ]].rename(columns={
        "player_name": "Hitter", "team_fg": "Team", "pa": "PA",
        "hr_to_date": "HR", "xhr": "xHR", "expected_remaining": "Rest",
        "projected": "Projected", "p10": "p10", "p90": "p90",
        **{c: f"{c[2:]}+ %" for c in milestone_cols},
    })
    for c in milestone_cols:
        display[f"{c[2:]}+ %"] = (display[f"{c[2:]}+ %"] * 100).round(1)
    table = display.round(1).to_html(index=False, border=0)

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Hitter HR projections - {projection.season}</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #16181d; }}
 table {{ border-collapse: collapse; font-variant-numeric: tabular-nums; }}
 th, td {{ padding: .35rem .7rem; text-align: right; border-bottom: 1px solid #dcdfe4; }}
 th:first-child, td:first-child {{ text-align: left; font-weight: 600; }}
 caption {{ text-align: left; padding-bottom: .75rem; color: #5b6270; }}
</style></head>
<body>
<h1>Projected individual home run totals</h1>
<p>{projection.season} regular season, as of {projection.as_of} &middot;
{result.sims:,} simulations</p>
{table}
</body></html>
"""


def to_records(projection: Projection, result: SimulationResult) -> list[dict]:
    df = _decorate(result.totals)
    return df.to_dict(orient="records")


def write_outputs(
    projection: Projection,
    result: SimulationResult,
    out_dir: Path,
    formats: tuple[str, ...] = ("json", "csv"),
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = projection.as_of
    written: list[Path] = []
    df = _decorate(result.totals)

    if "csv" in formats:
        path = out_dir / f"hr_projection_{stamp}.csv"
        df.to_csv(path, index=False)
        written.append(path)

    if "json" in formats:
        path = out_dir / f"hr_projection_{stamp}.json"
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "as_of": projection.as_of,
            "season": projection.season,
            "sims": result.sims,
            "seed": result.seed,
            "schedule_source": projection.schedule_source,
            "league_hr_per_pa": projection.league_hr_per_pa,
            "params": projection.params.__dict__,
            "teams": df.to_dict(orient="records"),
            "warnings": projection.warnings,
        }
        path.write_text(json.dumps(payload, indent=2, default=str))
        written.append(path)

    if "html" in formats:
        path = out_dir / f"hr_projection_{stamp}.html"
        path.write_text(_html(projection, result, df))
        written.append(path)

    return written


def _html(projection: Projection, result: SimulationResult, df: pd.DataFrame) -> str:
    display = df[[
        "team_fg", "hr_to_date", "games_remaining", "expected_remaining",
        "projected", "p10", "p90", "p_lead", "p_top3",
    ]].rename(columns={
        "team_fg": "Team", "hr_to_date": "HR", "games_remaining": "Games left",
        "expected_remaining": "Expected rest", "projected": "Projected",
        "p10": "p10", "p90": "p90", "p_lead": "Lead %", "p_top3": "Top 3 %",
    })
    display["Lead %"] = (display["Lead %"] * 100).round(1)
    display["Top 3 %"] = (display["Top 3 %"] * 100).round(1)
    table = display.round(1).to_html(index=False, border=0)

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Team HR projections - {projection.season}</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #16181d; }}
 table {{ border-collapse: collapse; font-variant-numeric: tabular-nums; }}
 th, td {{ padding: .35rem .7rem; text-align: right; border-bottom: 1px solid #dcdfe4; }}
 th:first-child, td:first-child {{ text-align: left; font-weight: 600; }}
 tr:first-child td {{ background: #f3f6ff; }}
 caption {{ text-align: left; padding-bottom: .75rem; color: #5b6270; }}
</style></head>
<body>
<h1>Team home run projections</h1>
<p>{projection.season} regular season, as of {projection.as_of} &middot;
{result.sims:,} simulations &middot; schedule: {projection.schedule_source}</p>
{table}
</body></html>
"""
