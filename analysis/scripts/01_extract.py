"""Extract the analysis columns from SQLite into a year-partitioned parquet snapshot.

Downstream scripts never touch SQLite: the parquet snapshot is the
reproducibility anchor and keeps analysis independent of an in-progress
backfill still writing to the database.
"""
from __future__ import annotations

import shutil
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from analysis import config
from analysis.lib import data as D

RAW_DIR = config.PARQUET_DIR / "raw"


def main() -> None:
    con = D.connect()
    D.attach_sqlite(con)

    cols = ", ".join(config.EXTRACT_COLUMNS)
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)

    con.execute(f"""
        COPY (
            SELECT {cols}
            FROM savant.statcast_pitches
            WHERE game_type = 'R'
              AND game_year BETWEEN {min(config.YEARS)} AND {max(config.YEARS)}
              AND pitch_type IS NOT NULL
              AND release_speed IS NOT NULL
        ) TO '{RAW_DIR}'
        (FORMAT PARQUET, PARTITION_BY (game_year), OVERWRITE_OR_IGNORE 1,
         COMPRESSION ZSTD)
    """)

    summary = con.execute(f"""
        SELECT game_year, COUNT(*) AS pitches
        FROM read_parquet('{RAW_DIR}/**/*.parquet', hive_partitioning=1)
        GROUP BY 1 ORDER BY 1
    """).df()
    print(summary.to_string(index=False))
    print(f"total: {int(summary['pitches'].sum()):,} pitches -> {RAW_DIR}")

    D.write_meta("s1_extract", {
        "rows_by_year": summary.to_dict(orient="records"),
        "columns": config.EXTRACT_COLUMNS,
    })
    con.close()


if __name__ == "__main__":
    main()
