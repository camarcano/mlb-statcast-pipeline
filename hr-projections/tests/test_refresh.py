import pandas as pd
import pytest

from hrproj import refresh as refresh_mod
from savant.db import get_fetch_log, upsert_fetch_log
from tests.conftest import make_pitch


def fake_fetch(calls, rows_per_day=2):
    def _fetch(date_str, game_types):
        calls.append(date_str)
        return pd.DataFrame([
            make_pitch(game_date=date_str, game_pk=int(date_str.replace("-", "")),
                       at_bat_number=i + 1)
            for i in range(rows_per_day)
        ])
    return _fetch


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    monkeypatch.setattr(refresh_mod, "rate_limit_pause", lambda: None)


def test_refresh_fetches_the_requested_window(empty_db, monkeypatch):
    calls = []
    monkeypatch.setattr(refresh_mod, "fetch_date", fake_fetch(calls))

    summary = refresh_mod.refresh_statcast(empty_db, "2026-08-23", days_back=3, force_days=0)

    assert calls == ["2026-08-21", "2026-08-22", "2026-08-23"]
    assert summary["inserted"] == 6
    assert not summary["failed"]


def test_completed_days_are_skipped_but_the_trailing_window_is_refetched(empty_db, monkeypatch):
    for day in ("2026-08-21", "2026-08-22", "2026-08-23"):
        upsert_fetch_log(day, "R", 100, "success", 1.0, db_path=empty_db)

    calls = []
    monkeypatch.setattr(refresh_mod, "fetch_date", fake_fetch(calls))
    summary = refresh_mod.refresh_statcast(empty_db, "2026-08-23", days_back=3, force_days=2)

    # The last two days are re-fetched even though they are logged as successful,
    # because a day pulled mid-game is logged complete while still missing innings.
    assert calls == ["2026-08-22", "2026-08-23"]
    assert summary["skipped"] == ["2026-08-21"]


def test_reinserting_the_same_day_adds_no_duplicates(empty_db, monkeypatch):
    monkeypatch.setattr(refresh_mod, "fetch_date", fake_fetch([]))
    first = refresh_mod.refresh_statcast(empty_db, "2026-08-23", days_back=1, force_days=1)
    second = refresh_mod.refresh_statcast(empty_db, "2026-08-23", days_back=1, force_days=1)

    assert first["inserted"] == 2
    assert second["inserted"] == 0


def test_one_bad_day_does_not_abort_the_run(empty_db, monkeypatch):
    calls = []
    good = fake_fetch(calls)

    def flaky(date_str, game_types):
        if date_str == "2026-08-22":
            raise RuntimeError("savant timeout")
        return good(date_str, game_types)

    monkeypatch.setattr(refresh_mod, "fetch_date", flaky)
    summary = refresh_mod.refresh_statcast(empty_db, "2026-08-23", days_back=3, force_days=0)

    assert list(summary["failed"]) == ["2026-08-22"]
    assert summary["fetched"] == ["2026-08-21", "2026-08-23"]
    assert get_fetch_log("2026-08-22", "R", db_path=empty_db)["fetch_status"] == "failed"
