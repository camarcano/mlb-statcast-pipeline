import sqlite3

import numpy as np
import pandas as pd
import pytest

from hrproj.data import (
    decay_weights,
    load_pa_frame,
    spray_angle,
    team_games_played,
    team_hr_to_date,
)
from tests.conftest import make_pitch, write_pitches


def read(db_path, start="2026-01-01", end="2026-12-31", season=2026):
    conn = sqlite3.connect(db_path)
    try:
        return load_pa_frame(conn, season, start, end)
    finally:
        conn.close()


def test_batting_team_follows_inning_half(tmp_path):
    db = tmp_path / "t.db"
    write_pitches(db, [
        make_pitch(inning_topbot="Top", at_bat_number=1, events="home_run", type="X"),
        make_pitch(inning_topbot="Bot", at_bat_number=2, events="home_run", type="X"),
    ])
    pa = read(db)

    assert set(pa["bat_team"]) == {"BOS", "NYY"}
    top = pa[pa["inning_topbot"] == "Top"].iloc[0]
    assert top["bat_team"] == "BOS"      # away team bats in the top half
    assert top["pitch_team"] == "NYY"
    assert top["venue"] == "NYY"         # venue is always the home club's park


def test_non_pa_events_are_excluded(tmp_path):
    db = tmp_path / "t.db"
    write_pitches(db, [
        make_pitch(at_bat_number=1, events="single", type="X"),
        make_pitch(at_bat_number=2, events="caught_stealing_2b"),
        make_pitch(at_bat_number=3, events="wild_pitch"),
        make_pitch(at_bat_number=4, events="walk"),
    ])
    pa = read(db)
    assert len(pa) == 2
    assert set(pa["events"]) == {"single", "walk"}


def test_other_game_types_and_seasons_are_excluded(tmp_path):
    db = tmp_path / "t.db"
    write_pitches(db, [
        make_pitch(at_bat_number=1, events="home_run", type="X"),
        make_pitch(at_bat_number=2, events="home_run", type="X", game_type="S"),
        make_pitch(at_bat_number=3, events="home_run", type="X",
                   game_year=2025, game_date="2025-04-01"),
    ])
    pa = read(db)
    assert len(pa) == 1


def test_spray_angle_sign_is_pull_relative():
    hc_x = pd.Series([60.0, 60.0, 190.0, 190.0])   # left field, then right field
    hc_y = pd.Series([100.0, 100.0, 100.0, 100.0])
    stand = pd.Series(["R", "L", "R", "L"])
    spray = spray_angle(hc_x, hc_y, stand)

    assert spray[0] > 0    # right-handed hitter pulling to left
    assert spray[1] < 0    # left-handed hitter going oppo to left
    assert spray[2] < 0
    assert spray[3] > 0


def test_air_flag_bounds(tmp_path):
    db = tmp_path / "t.db"
    write_pitches(db, [
        make_pitch(at_bat_number=1, type="X", events="field_out",
                   launch_speed=95.0, launch_angle=5.0),    # too flat
        make_pitch(at_bat_number=2, type="X", events="field_out",
                   launch_speed=95.0, launch_angle=25.0),   # air
        make_pitch(at_bat_number=3, type="X", events="field_out",
                   launch_speed=95.0, launch_angle=60.0),   # popup above the band
    ])
    pa = read(db).sort_values("at_bat_number")
    assert list(pa["is_air"]) == [False, True, False]
    assert list(pa["is_bbe"]) == [True, True, True]


def test_decay_weights_halve_at_the_half_life():
    dates = pd.Series(pd.to_datetime(["2026-08-23", "2026-07-09", "2026-05-25"]))
    w = decay_weights(dates, "2026-08-23", half_life_days=45)
    assert w.iloc[0] == pytest.approx(1.0)
    assert w.iloc[1] == pytest.approx(0.5, abs=0.02)
    assert w.iloc[2] == pytest.approx(0.25, abs=0.02)


def test_team_aggregates(league_db):
    pa = read(league_db)
    games = team_games_played(pa)
    hrs = team_hr_to_date(pa)

    assert set(games.index) == {"NYY", "BOS", "TOR", "TB"}
    assert (games == 36).all()          # 3 opponents x 12 games
    assert hrs.sum() == pa["is_hr"].sum()
