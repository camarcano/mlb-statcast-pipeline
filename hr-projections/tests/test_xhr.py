import numpy as np
import pandas as pd
import pytest

from hrproj.config import DEFAULT_PARAMS
from hrproj.xhr import build_grid, expected_hr_per_pa, spray_bucket


def synthetic_bbe(n=30000, seed=3):
    """Batted balls whose HR probability rises with EV, peaks near 28 degrees, and favours pulls."""
    rng = np.random.default_rng(seed)
    ev = rng.normal(90, 12, n)
    la = rng.normal(12, 22, n)
    spray = rng.normal(0, 25, n)
    logit = (ev - 100) * 0.35 - np.abs(la - 28) * 0.25 + (spray > 15) * 0.6
    hr = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(float)
    return pd.DataFrame({
        "launch_speed": ev, "launch_angle": la, "spray": spray, "is_hr": hr,
    })


@pytest.fixture(scope="module")
def grid():
    return build_grid(synthetic_bbe(), DEFAULT_PARAMS)


def test_spray_buckets_partition_the_field():
    spray = pd.Series([-40.0, -5.0, 0.0, 5.0, 40.0, np.nan])
    assert list(spray_bucket(spray)) == [0, 1, 1, 1, 2, -1]


def test_probability_rises_with_exit_velocity(grid):
    la = np.full(5, 28.0)
    ev = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
    probs = grid.probability(ev, la, np.full(5, 2))
    assert np.all(np.diff(probs) > 0)


def test_probability_peaks_in_the_home_run_window(grid):
    ev = np.full(5, 105.0)
    la = np.array([5.0, 15.0, 28.0, 40.0, 55.0])
    probs = grid.probability(ev, la, np.full(5, 2))
    assert probs.argmax() == 2


def test_pulled_contact_beats_oppo_contact(grid):
    ev, la = np.array([104.0]), np.array([27.0])
    pulled = grid.probability(ev, la, np.array([2]))[0]
    oppo = grid.probability(ev, la, np.array([0]))[0]
    assert pulled > oppo


def test_grid_totals_track_actual_home_runs(grid):
    bbe = synthetic_bbe()
    xhr = grid.probability(
        bbe["launch_speed"].to_numpy(),
        bbe["launch_angle"].to_numpy(),
        spray_bucket(bbe["spray"]),
    ).sum()
    assert xhr == pytest.approx(bbe["is_hr"].sum(), rel=0.05)


def test_probabilities_stay_in_range(grid):
    ev = np.array([-50.0, 0.0, 200.0, np.nan])
    la = np.array([0.0, 90.0, 30.0, 30.0])
    probs = grid.probability(ev, la)
    assert np.all(probs >= 0) and np.all(probs <= 1)
    assert probs[-1] == 0.0


def test_empty_input_yields_zero_grid():
    empty = pd.DataFrame(columns=["launch_speed", "launch_angle", "spray", "is_hr"])
    g = build_grid(empty, DEFAULT_PARAMS)
    assert g.probability(np.array([105.0]), np.array([28.0]))[0] == 0.0


def test_expected_hr_is_zero_for_balls_not_in_play(grid):
    pa = pd.DataFrame({
        "is_bbe": [False, True],
        "launch_speed": [np.nan, 105.0],
        "launch_angle": [np.nan, 28.0],
        "spray": [np.nan, 20.0],
    })
    xhr = expected_hr_per_pa(pa, grid)
    assert xhr.iloc[0] == 0.0
    assert xhr.iloc[1] > 0.3


def bbia_frame(n_bbia=100, n_other=900, hr=53):
    """A synthetic league: `n_bbia` hard air balls, `hr` of which left the yard."""
    rows = []
    for i in range(n_bbia):
        rows.append({"is_bbia100": True, "is_hr": 1.0 if i < hr else 0.0})
    for _ in range(n_other):
        rows.append({"is_bbia100": False, "is_hr": 0.0})
    return pd.DataFrame(rows)


def test_league_ratio_is_home_runs_per_hard_air_ball():
    from hrproj.xhr import league_hr_per_bbia

    assert league_hr_per_bbia(bbia_frame()) == pytest.approx(0.53)
    empty = pd.DataFrame({"is_bbia100": [False], "is_hr": [0.0]})
    assert league_hr_per_bbia(empty) == 0.0        # no divide by zero


def test_bbia_estimator_is_calibrated_to_the_league_total():
    """Scored at the league ratio, expected home runs equal the ones actually hit."""
    from hrproj.xhr import bbia_expected_hr, league_hr_per_bbia

    league = bbia_frame()
    estimate = bbia_expected_hr(league, league_hr_per_bbia(league))
    assert estimate.sum() == pytest.approx(league["is_hr"].sum())
    # Nothing is credited to contact that was not hard and in the air.
    assert estimate[~league["is_bbia100"]].eq(0).all()


def test_blend_features_endpoints_and_middle():
    from hrproj.xhr import blend_features

    a = pd.Series([1.0, 2.0, 3.0])
    b = pd.Series([0.0, 0.0, 6.0])

    pd.testing.assert_series_equal(blend_features(a, b, 0.0), a)
    pd.testing.assert_series_equal(blend_features(a, b, 1.0), b)
    assert blend_features(a, b, 0.5).tolist() == [0.5, 1.0, 4.5]
    # Out-of-range weights are clamped rather than extrapolated.
    pd.testing.assert_series_equal(blend_features(a, b, -1.0), a)
    pd.testing.assert_series_equal(blend_features(a, b, 5.0), b)
