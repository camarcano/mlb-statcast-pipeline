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


def test_refresh_window_covers_everything_since_the_last_stored_game(season):
    """Run it after a fortnight away and it should fetch the fortnight, not seven days."""
    from hrproj.cli import _refresh_window

    db, pa = season
    latest = str(pa["game_date"].max().date())
    end = str((pa["game_date"].max() + pd.Timedelta(days=14)).date())

    assert _refresh_window(db, 2026, end, None) == 15
    assert _refresh_window(db, 2026, latest, None) == 2      # never less than the forced window
    assert _refresh_window(db, 2026, end, 3) == 3            # an explicit request still wins


def test_refresh_window_is_zero_without_a_database(tmp_path):
    from hrproj.cli import _refresh_window

    assert _refresh_window(tmp_path / "missing.db", 2026, "2026-08-23", None) == 0


def test_project_explains_how_to_backfill_an_empty_database(tmp_path, monkeypatch):
    """Refreshing cannot rescue an empty database, so say what will."""
    from savant.db import init_db

    db = tmp_path / "empty.db"
    init_db(db)
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))

    result = CliRunner().invoke(cli, ["project", "--no-schedule"])
    assert result.exit_code != 0
    assert "statcast backfill" in result.output


def test_leaders_command_reports_milestone_odds(season, monkeypatch, tmp_path):
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))
    monkeypatch.setenv("HRPROJ_OUT_DIR", str(tmp_path / "out"))

    result = CliRunner().invoke(cli, [
        "leaders", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "300", "--milestone", "10", "--top", "5", "--format", "csv",
    ])

    assert result.exit_code == 0, result.output
    assert "Projected individual home run totals" in result.output
    assert "10+" in result.output
    assert "chance of 10+ home runs" in result.output
    assert (tmp_path / "out" / "hr_players_2026-06-01.csv").exists()


def test_leaders_reach_option_sizes_the_table(season, monkeypatch, tmp_path):
    """--reach prints everyone above a probability instead of a fixed row count."""
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))

    invoke = lambda args: CliRunner().invoke(cli, [
        "leaders", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "300", "--milestone", "5", *args,
    ])
    strict = invoke(["--reach", "0.99"])
    loose = invoke(["--reach", "0.01"])

    assert strict.exit_code == 0 and loose.exit_code == 0
    assert len(loose.output.splitlines()) > len(strict.output.splitlines())


def test_leaders_reach_filters_by_probability_not_row_count(season, monkeypatch, tmp_path):
    """Every hitter printed must actually clear the bar, in probability order or not."""
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))
    monkeypatch.setenv("HRPROJ_OUT_DIR", str(tmp_path / "out"))

    result = CliRunner().invoke(cli, [
        "leaders", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "400", "--milestone", "40", "--reach", "0.10", "--format", "csv",
    ])
    assert result.exit_code == 0, result.output

    # The export keeps every hitter; only the console view is filtered.
    written = pd.read_csv(tmp_path / "out" / "hr_players_2026-06-01.csv")
    qualifying = written[written["p_40"] >= 0.10]
    assert 0 < len(qualifying) < len(written)      # a real cut, not all or nothing

    printed_rows = [
        line for line in result.output.splitlines()
        if line and line[0].isalpha() and line.rstrip().endswith("%")
    ]
    assert len(printed_rows) == len(qualifying)


def test_project_shows_base_and_alternate_columns(season, monkeypatch, tmp_path):
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))
    monkeypatch.setenv("HRPROJ_OUT_DIR", str(tmp_path / "out"))

    result = CliRunner().invoke(cli, [
        "project", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "200", "--format", "csv",
    ])
    assert result.exit_code == 0, result.output
    for column in ("BBIA", "ProjA", "LeadA%", "Proj", "Lead%"):
        assert column in result.output

    written = pd.read_csv(tmp_path / "out" / "hr_projection_2026-06-01.csv")
    assert {"bbia", "projected", "projected_alt", "p_lead_alt"} <= set(written.columns)
    assert (written["bbia"] >= 0).all()


def test_leaders_shows_base_and_alternate_columns(season, monkeypatch, tmp_path):
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))
    monkeypatch.setenv("HRPROJ_OUT_DIR", str(tmp_path / "out"))

    result = CliRunner().invoke(cli, [
        "leaders", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "200", "--milestone", "20", "--top", "5", "--format", "csv",
    ])
    assert result.exit_code == 0, result.output
    for column in ("BBIA", "ProjA", "20+A"):
        assert column in result.output

    written = pd.read_csv(tmp_path / "out" / "hr_players_2026-06-01.csv")
    assert {"bbia", "projected", "projected_alt", "p_20_alt"} <= set(written.columns)


def test_no_alt_restores_the_original_table(season, monkeypatch, tmp_path):
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))

    result = CliRunner().invoke(cli, [
        "project", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
        "--sims", "200", "--no-alt",
    ])
    assert result.exit_code == 0, result.output
    assert "Proj" in result.output
    assert "ProjA" not in result.output
    assert "BBIA" not in result.output


def test_the_alternate_leaves_the_base_columns_untouched(season, monkeypatch, tmp_path):
    """Adding the alternate must not perturb the numbers it sits beside."""
    db, _ = season
    monkeypatch.setenv("HRPROJ_STATCAST_DB", str(db))
    monkeypatch.setenv("HRPROJ_CACHE_DB", str(tmp_path / "cache.db"))
    monkeypatch.setenv("HRPROJ_OUT_DIR", str(tmp_path / "out"))

    args = ["project", "--no-refresh", "--no-schedule", "--as-of", "2026-06-01",
            "--sims", "200", "--format", "csv"]
    assert CliRunner().invoke(cli, args + ["--no-alt"]).exit_code == 0
    without = pd.read_csv(tmp_path / "out" / "hr_projection_2026-06-01.csv")
    assert CliRunner().invoke(cli, args).exit_code == 0
    with_alt = pd.read_csv(tmp_path / "out" / "hr_projection_2026-06-01.csv")

    shared = ["team", "hr_to_date", "projected", "p10", "p90", "p_lead", "p_top3"]
    pd.testing.assert_frame_equal(without[shared], with_alt[shared])


def test_backtest_honours_the_bbia_weight(season):
    """The weight must reach the model, not be quietly dropped by the backtest."""
    from hrproj.backtest import run_backtest

    _, pa = season
    cutoff = str(pa["game_date"].quantile(0.6).date())
    end = str(pa["game_date"].max().date())

    base = run_backtest(pa, cutoff, end, 2026, DEFAULT_PARAMS)
    alt = run_backtest(pa, cutoff, end, 2026, DEFAULT_PARAMS.replace(bbia_weight=1.0))

    base_mae = base.scores.set_index("method").loc["model", "mae"]
    alt_mae = alt.scores.set_index("method").loc["model", "mae"]
    assert base_mae != alt_mae
