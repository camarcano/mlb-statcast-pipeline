import pandas as pd

from savant.db import (
    get_connection,
    get_fetch_log,
    get_pitch_count_for_date,
    init_db,
    insert_pitches,
    upsert_fetch_log,
)


def test_init_db_creates_tables(tmp_db):
    conn = get_connection(tmp_db)
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    conn.close()

    assert "statcast_pitches" in tables
    assert "fetch_log" in tables
    assert "schema_version" in tables


def test_init_db_idempotent(tmp_db):
    init_db(tmp_db)
    conn = get_connection(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM statcast_pitches").fetchone()[0]
    conn.close()
    assert count == 0


def test_insert_pitches(tmp_db, sample_df):
    inserted = insert_pitches(sample_df, tmp_db)
    assert inserted == 1

    count = get_pitch_count_for_date("2026-05-03", db_path=tmp_db)
    assert count == 1


def test_insert_pitches_dedup(tmp_db, sample_df):
    insert_pitches(sample_df, tmp_db)
    inserted = insert_pitches(sample_df, tmp_db)
    assert inserted == 0

    count = get_pitch_count_for_date("2026-05-03", db_path=tmp_db)
    assert count == 1


def test_insert_empty_df(tmp_db):
    df = pd.DataFrame()
    inserted = insert_pitches(df, tmp_db)
    assert inserted == 0


def test_upsert_fetch_log(tmp_db):
    upsert_fetch_log("2026-05-03", "R", 4240, "success", 5.2, db_path=tmp_db)

    log = get_fetch_log("2026-05-03", "R", tmp_db)
    assert log is not None
    assert log["fetch_status"] == "success"
    assert log["row_count"] == 4240


def test_upsert_fetch_log_replaces(tmp_db):
    upsert_fetch_log("2026-05-03", "R", 100, "pending", 0, db_path=tmp_db)
    upsert_fetch_log("2026-05-03", "R", 4240, "success", 5.2, db_path=tmp_db)

    log = get_fetch_log("2026-05-03", "R", tmp_db)
    assert log["fetch_status"] == "success"
    assert log["row_count"] == 4240


def test_get_fetch_log_missing(tmp_db):
    log = get_fetch_log("2099-01-01", "R", tmp_db)
    assert log is None


def test_wal_mode_enabled(tmp_db):
    conn = get_connection(tmp_db)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"
