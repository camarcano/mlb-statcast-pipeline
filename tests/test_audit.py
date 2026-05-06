from savant.audit import find_duplicates, find_gaps, verify_date, verify_row_counts, get_status
from savant.db import insert_pitches, upsert_fetch_log, init_db, get_connection


def test_find_duplicates_none(tmp_db, sample_df):
    insert_pitches(sample_df, tmp_db)
    dups = find_duplicates(tmp_db)
    assert dups == []


def test_verify_date_valid(tmp_db, sample_df):
    insert_pitches(sample_df, tmp_db)
    upsert_fetch_log("2026-05-03", "R", 1, "success", 1.0, db_path=tmp_db)

    result = verify_date("2026-05-03", tmp_db)
    assert result["total_rows"] == 1
    assert result["errors"] == []


def test_verify_date_missing(tmp_db):
    result = verify_date("2099-01-01", tmp_db)
    assert "No rows found" in result["errors"][0]


def test_verify_row_counts_match(tmp_db, sample_df):
    insert_pitches(sample_df, tmp_db)
    upsert_fetch_log("2026-05-03", "R", 1, "success", 1.0, db_path=tmp_db)

    mismatches = verify_row_counts(tmp_db)
    assert mismatches == []


def test_get_status(tmp_db, sample_df):
    insert_pitches(sample_df, tmp_db)

    status = get_status(tmp_db)
    assert status["total_rows"] == 1
    assert status["date_range"]["min"] == "2026-05-03"
    assert status["date_range"]["max"] == "2026-05-03"


def test_find_gaps_no_data(tmp_db):
    gaps = find_gaps(2025, tmp_db)
    assert len(gaps) > 0
    assert gaps[0]["count"] > 0
