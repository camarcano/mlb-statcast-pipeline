import sqlite3

import pandas as pd
import pytest
from click.testing import CliRunner

from hrproj.backtest import run_backtest, schedule_from_played, score, sweep
from hrproj.cli import cli
from hrproj.config import DEFAULT_PARAMS
from hrproj.data import load_pa_frame
from tests.conftest import synth_league, write_pitches


@pytest.fixture(scope="module")
def season(tmp_path_factory):
    db = tmp_path_factory.mktemp("bt") / "league.db"
    write_pitches(db, synth_league(
        games_per_matchup=20,
        hr_talent={"NYY": 0.055, "BOS": 0.04, "TOR": 0.025, "TB": 0.02},
    ))
    conn = sqlite3.connect(db)
    pa = load_pa_frame(conn, 2026, "2026-01-01", "2026-12-31")
    conn.close()
    return db, pa


def test_schedule_from_played_yields_two_rows_per_game(season):
    _, pa = season
    played = schedule_from_played(pa)
    assert len(played) == pa["game_pk"].nunique() * 2
    assert {m["team"] for m in played} == set(pa["bat_team"].unique())
    assert all(m["venue_team"] is not None for m in played)


def test_backtest_scores_the_model_against_the_baselines(season):
    _, pa = season
    cutoff = str(pa["game_date"].quantile(0.6).date())
    end = str(pa["game_date"].max().date())

    result = run_backtest(pa, cutoff, end, 2026, DEFAULT_PARAMS)

    assert set(result.scores["method"]) == {"model", "hr_per_game", "xhr_per_game", "league"}
    assert (result.scores["mae"] >= 0).all()
    # The model must at least beat pretending every club is league average.
    model_mae = result.scores.set_index("method").loc["model", "mae"]
    league_mae = result.scores.set_index("method").loc["league", "mae"]
    assert model_mae < league_mae
    assert len(result.per_team) == 4


def test_backtest_rejects_a_cutoff_with_nothing_on_one_side(season):
    _, pa = season
    with pytest.raises(ValueError):
        run_backtest(pa, "2026-01-01", "2026-12-31", 2026, DEFAULT_PARAMS)


def test_score_flags_a_biased_method():
    per_team = pd.DataFrame({
        "actual": [10.0, 20.0, 30.0],
        "high": [15.0, 25.0, 35.0],
        "exact": [10.0, 20.0, 30.0],
    })
    scores = score(per_team, ["exact", "high"]).set_index("method")
    assert scores.loc["exact", "mae"] == 0
    assert scores.loc["high", "bias"] == pytest.approx(5.0)


def test_sweep_explores_the_grid(season):
    _, pa = season
    cutoff = str(pa["game_date"].quantile(0.6).date())
    end = str(pa["game_date"].max().date())

    table = sweep(
        pa, cutoff, end, 2026, DEFAULT_PARAMS,
        half_lives=(30, 60), phis=(0.0, 1.0), ks=(100, 300),
    )
    assert len(table) == 8
    assert table["mae"].is_monotonic_increasing      # sorted best first


def test_project_command_runs_end_to_end(season, monkeypatch, tmp_path):
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))
    monkeypatch.setenv("HRPROJ_OUT_DIR", str(tmp_path / "out"))

    result = CliRunner().invoke(cli, [
        "project", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "200", "--format", "json,csv",
    ])

    assert result.exit_code == 0, result.output
    assert "Team home run projections" in result.output
    assert "Favourite:" in result.output
    assert (tmp_path / "out" / "hr_projection_2026-06-01.json").exists()
    assert (tmp_path / "out" / "hr_projection_2026-06-01.csv").exists()


def test_players_command_lists_contributors(season, monkeypatch, tmp_path):
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))

    result = CliRunner().invoke(cli, ["players", "NYY", "--as-of", "2026-06-01"])
    assert result.exit_code == 0, result.output
    assert "NYY" in result.output
    assert "RoS HR" in result.output


def test_project_reports_a_missing_database(monkeypatch, tmp_path):
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(tmp_path / "nope.db"))
    result = CliRunner().invoke(cli, ["project", "--no-refresh", "--no-schedule"])
    assert result.exit_code != 0
    assert "not found" in result.output
