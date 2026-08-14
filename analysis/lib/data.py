"""DuckDB access helpers.

The SQLite database is the ingest target; analysis reads a year-partitioned
parquet snapshot instead so that long-running study scripts are decoupled from
the backfill still writing to SQLite.
"""
from __future__ import annotations

import json

import subprocess
from pathlib import Path

import duckdb

from analysis import config


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    return con


def attach_sqlite(con: duckdb.DuckDBPyConnection, db_path: Path | None = None) -> None:
    """Attach the ingest SQLite database read-only as schema `savant`."""
    path = str(db_path or config.DB_PATH)
    con.execute("INSTALL sqlite")
    con.execute("LOAD sqlite")
    con.execute(f"ATTACH '{path}' AS savant (TYPE sqlite, READ_ONLY)")


def pitches_glob() -> str:
    return str(config.PARQUET_DIR / "pitches" / "**" / "*.parquet")


def arsenal_path() -> Path:
    return config.PARQUET_DIR / "arsenal.parquet"


def load_pitches(
    columns: list[str] | None = None,
    years: list[int] | None = None,
    families: list[str] | None = None,
    where: str | None = None,
):
    """Read the pitch-grain parquet snapshot into a pandas DataFrame."""
    con = connect()
    cols = ", ".join(columns) if columns else "*"
    clauses = []
    if years:
        clauses.append("game_year IN (" + ",".join(str(y) for y in years) + ")")
    if families:
        quoted = ",".join(f"'{f}'" for f in families)
        clauses.append(f"family IN ({quoted})")
    if where:
        clauses.append(f"({where})")
    filt = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT {cols} FROM read_parquet('{pitches_glob()}', hive_partitioning=1){filt}"
    df = con.execute(sql).df()
    con.close()
    return df


def query(sql: str):
    """Run a DuckDB query with `pitches` available as a view over the snapshot."""
    con = connect()
    con.execute(
        f"CREATE VIEW pitches AS SELECT * FROM "
        f"read_parquet('{pitches_glob()}', hive_partitioning=1)"
    )
    if arsenal_path().exists():
        con.execute(
            f"CREATE VIEW arsenal AS SELECT * FROM read_parquet('{arsenal_path()}')"
        )
    df = con.execute(sql).df()
    con.close()
    return df


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=config.REPO_ROOT, text=True,
        ).strip()
    except Exception:
        return "unknown"


def write_meta(name: str, payload: dict) -> Path:
    """Write a per-script metadata sidecar (git SHA + parameters + summary)."""
    out = config.RESULTS_DIR / f"{name}_meta.json"
    body = {"git_sha": git_sha(), **payload}
    out.write_text(json.dumps(body, indent=2, default=str))
    return out


def save_result(df, name: str) -> Path:
    """Persist a small results table as CSV under analysis/results/."""
    out = config.RESULTS_DIR / f"{name}.csv"
    df.to_csv(out, index=False)
    return out


def pitcher_name_map() -> dict[int, str]:
    """MLBAM pitcher id -> name, from the repo's roster file.

    Savant's `player_name` column names the batter on a pitch row, never the
    pitcher, so pitcher labels have to come from this side lookup. Missing ids
    simply fall back to the raw number at display time.
    """
    path = config.REPO_ROOT / "data" / "pitcher_names.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {int(k): v for k, v in raw.items()}
