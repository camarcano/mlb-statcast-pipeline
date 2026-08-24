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
