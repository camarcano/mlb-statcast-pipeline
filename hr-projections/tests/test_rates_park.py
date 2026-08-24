import sqlite3

import numpy as np
import pandas as pd
import pytest

from hrproj.config import DEFAULT_PARAMS
from hrproj.data import load_pa_frame
from hrproj.park import opponent_factors, park_factors
from hrproj.rates import batter_rates, league_hr_per_pa


def pa_frame(db):
    conn = sqlite3.connect(db)
    try:
        return load_pa_frame(conn, 2026, "2026-01-01", "2026-12-31")
    finally:
        conn.close()


def test_small_samples_regress_hard_toward_the_league(league_db):
    pa = pa_frame(league_db)
    xhr = pd.Series(np.zeros(len(pa)), index=pa.index)
    rates = batter_rates(pa, xhr, "2026-08-23", DEFAULT_PARAMS)
    league = rates.attrs["league_mu"]

    # A call-up who homered in his only plate appearance must not project at 1.000.
    debut = pa.iloc[[-1]].copy()
    debut["batter"] = 999999
    debut["is_hr"] = 1.0
    with_debut = pd.concat([pa, debut], ignore_index=True)
    single = batter_rates(
        with_debut,
        pd.Series(np.zeros(len(with_debut)), index=with_debut.index),
        "2026-08-23",
        DEFAULT_PARAMS,
    ).set_index("batter")
    assert single.loc[999999, "rate"] < 0.05
    assert single.loc[999999, "rate"] > league * 0.9   # but still above the mean
    assert rates["rate"].between(0, 0.25).all()
    assert league > 0


def test_phi_controls_the_weight_on_expected_home_runs(league_db):
    pa = pa_frame(league_db)
    # Expected home runs everywhere, actual home runs nowhere.
    xhr = pd.Series(np.full(len(pa), 0.05), index=pa.index)
    pa = pa.assign(is_hr=0.0)

    all_actual = batter_rates(pa, xhr, "2026-08-23", DEFAULT_PARAMS.replace(phi=0.0))
    all_expected = batter_rates(pa, xhr, "2026-08-23", DEFAULT_PARAMS.replace(phi=1.0))

    assert all_expected["rate"].mean() > all_actual["rate"].mean()


def test_posterior_parameters_stay_positive(league_db):
    pa = pa_frame(league_db)
    xhr = pd.Series(np.full(len(pa), 0.9), index=pa.index)   # absurdly high on purpose
    rates = batter_rates(pa, xhr, "2026-08-23", DEFAULT_PARAMS)
    assert (rates["alpha"] > 0).all()
    assert (rates["beta"] > 0).all()


def test_a_traded_hitter_is_assigned_their_latest_team(tmp_path):
    from tests.conftest import make_pitch, write_pitches

    db = tmp_path / "trade.db"
    write_pitches(db, [
        make_pitch(game_date="2026-05-01", game_pk=1, at_bat_number=1,
                   home_team="NYY", away_team="BOS", inning_topbot="Top", batter=55),
        make_pitch(game_date="2026-08-01", game_pk=2, at_bat_number=1,
                   home_team="TOR", away_team="TB", inning_topbot="Bot", batter=55),
    ])
    pa = pa_frame(db)
    rates = batter_rates(pa, pd.Series(np.zeros(len(pa)), index=pa.index),
                         "2026-08-23", DEFAULT_PARAMS)
    assert rates.set_index("batter").loc[55, "team"] == "TOR"


def test_league_rate_matches_a_hand_count(league_db):
    pa = pa_frame(league_db)
    # With an infinite half-life the weighted rate is just HR / PA.
    flat = league_hr_per_pa(pa, "2026-08-23", DEFAULT_PARAMS.replace(half_life_days=1e9))
    assert flat == pytest.approx(pa["is_hr"].sum() / len(pa), rel=1e-6)


def test_park_factors_shrink_toward_neutral():
    n = 400
    rows = []
    for venue, hr_rate in (("COL", 0.30), ("SF", 0.02)):
        for i in range(n):
            rows.append({
                "venue": venue, "pitch_team": "XXX", "is_air": True,
                "is_hr": 1.0 if i < hr_rate * n else 0.0,
            })
    pa = pd.DataFrame(rows)

    factors = park_factors(pa, DEFAULT_PARAMS)
    raw_ratio = 0.30 / 0.16
    assert 1.0 < factors["COL"] < raw_ratio      # pulled in, not ignored
    assert factors["SF"] < 1.0
    assert factors["COL"] > factors["SF"]


def test_opponent_factors_are_park_neutralised():
    """A staff pitching in a launching pad is not blamed for the park."""
    rows = []
    for i in range(2000):
        rows.append({"venue": "COL", "pitch_team": "ROCKS", "is_air": True,
                     "is_hr": 1.0 if i % 4 == 0 else 0.0})     # .250 allowed in a hitter's park
    for i in range(2000):
        rows.append({"venue": "SF", "pitch_team": "GIANTS", "is_air": True,
                     "is_hr": 1.0 if i % 8 == 0 else 0.0})     # .125 in a pitcher's park
    pa = pd.DataFrame(rows)

    parks = park_factors(pa, DEFAULT_PARAMS)
    raw = pd.Series({"ROCKS": 0.25, "GIANTS": 0.125}) / 0.1875
    adjusted = opponent_factors(pa, parks, DEFAULT_PARAMS)

    # Both staffs move toward each other once their parks are divided out.
    assert adjusted["ROCKS"] < raw["ROCKS"]
    assert adjusted["GIANTS"] > raw["GIANTS"]
