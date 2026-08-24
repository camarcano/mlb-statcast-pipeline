import sqlite3

import numpy as np
import pandas as pd
import pytest

from hrproj.config import DEFAULT_PARAMS
from hrproj.data import load_pa_frame
from hrproj.model import build_projection
from hrproj.simulate import _leader_probability, _top_n_probability, simulate
from tests.conftest import synth_league, write_pitches

TEAMS = ("NYY", "BOS", "TOR", "TB")


def frame(db):
    conn = sqlite3.connect(db)
    try:
        return load_pa_frame(conn, 2026, "2026-01-01", "2026-12-31")
    finally:
        conn.close()


def remaining_games(teams=TEAMS, per_team=10, venue=True):
    games = []
    for i, team in enumerate(teams):
        for g in range(per_team):
            opponent = teams[(i + 1) % len(teams)]
            games.append({
                "game_pk": 90000 + i * 100 + g,
                "game_date": "2026-09-01",
                "team": team,
                "opponent": opponent,
                "home": g % 2 == 0,
                "venue_team": team if venue else None,
            })
    return games


@pytest.fixture(scope="module")
def projection(tmp_path_factory):
    db = tmp_path_factory.mktemp("model") / "league.db"
    write_pitches(db, synth_league(
        hr_talent={"NYY": 0.06, "BOS": 0.035, "TOR": 0.02, "TB": 0.02}
    ))
    pa = frame(db)
    params = DEFAULT_PARAMS.replace(sims=2000)
    return build_projection(pa, remaining_games(), "2026-06-30", 2026, params)


def test_every_team_gets_inputs(projection):
    assert set(projection.teams) == set(TEAMS)
    for team in TEAMS:
        ti = projection.teams[team]
        assert ti.games_remaining == 10
        assert ti.pa_per_game > 0
        assert ti.batters["share"].sum() == pytest.approx(1.0)


def test_the_stronger_offence_projects_higher(projection):
    assert projection.teams["NYY"].expected_remaining > projection.teams["TOR"].expected_remaining
    assert projection.teams["NYY"].projected > projection.teams["TOR"].projected


def test_projection_equals_current_plus_expected(projection):
    ti = projection.teams["NYY"]
    assert ti.projected == pytest.approx(ti.hr_to_date + ti.expected_remaining)
    assert ti.expected_remaining == pytest.approx(
        ti.point_rate * ti.pa_per_game * ti.context_sum
    )


def test_disabling_context_sets_multipliers_to_one(tmp_path):
    db = tmp_path / "league.db"
    write_pitches(db, synth_league())
    pa = frame(db)
    params = DEFAULT_PARAMS.replace(use_park=False, use_opponent=False, sims=200)
    proj = build_projection(pa, remaining_games(), "2026-06-30", 2026, params)
    for team in TEAMS:
        assert proj.teams[team].context_sum == pytest.approx(10.0)


def test_simulation_is_reproducible(projection):
    first = simulate(projection).totals
    second = simulate(projection).totals
    pd.testing.assert_frame_equal(first, second)


def test_simulation_summary_is_coherent(projection):
    result = simulate(projection)
    totals = result.totals.set_index("team")

    assert result.totals["p_lead"].sum() == pytest.approx(1.0)
    assert result.totals["p_top3"].sum() == pytest.approx(3.0)
    for team in TEAMS:
        row = totals.loc[team]
        assert row["p10"] <= row["median"] <= row["p90"]
        assert row["projected"] >= row["hr_to_date"]
        assert 0.0 <= row["p_lead"] <= 1.0
    assert totals.loc["NYY", "p_lead"] > totals.loc["TOR", "p_lead"]


def test_teams_with_no_games_left_keep_their_current_total(tmp_path):
    db = tmp_path / "league.db"
    write_pitches(db, synth_league())
    pa = frame(db)
    params = DEFAULT_PARAMS.replace(sims=500)
    proj = build_projection(pa, [], "2026-06-30", 2026, params)

    result = simulate(proj)
    assert (result.totals["projected"] == result.totals["hr_to_date"]).all()
    assert proj.warnings                      # the missing schedule is reported, not hidden


def test_leader_probability_splits_ties():
    matrix = np.array([[5, 5, 3], [6, 1, 1]])
    probs = _leader_probability(matrix)
    assert probs == pytest.approx([0.75, 0.25, 0.0])


def test_top_n_probability_accounts_for_ties_at_the_cut():
    matrix = np.array([[9, 5, 5, 1]])
    probs = _top_n_probability(matrix, 2)
    assert probs == pytest.approx([1.0, 0.5, 0.5, 0.0])


def test_league_normalisation_matches_the_league_rate(projection):
    """Aggregate projected rate should land on the league rate, not above it."""
    weight = sum(ti.pa_per_game for ti in projection.teams.values())
    aggregate = sum(
        ti.point_rate * ti.pa_per_game for ti in projection.teams.values()
    ) / weight
    assert aggregate == pytest.approx(projection.league_hr_per_pa, rel=1e-6)
    assert projection.normalization != 1.0     # the correction actually did something


def test_normalisation_can_be_switched_off(tmp_path):
    db = tmp_path / "league.db"
    write_pitches(db, synth_league())
    pa = frame(db)
    params = DEFAULT_PARAMS.replace(league_normalize=False, sims=100)
    proj = build_projection(pa, remaining_games(), "2026-06-30", 2026, params)
    assert proj.normalization == 1.0


def test_normalisation_preserves_the_ordering_between_teams(tmp_path):
    db = tmp_path / "league.db"
    write_pitches(db, synth_league(
        hr_talent={"NYY": 0.06, "BOS": 0.035, "TOR": 0.02, "TB": 0.02}
    ))
    pa = frame(db)
    games = remaining_games()
    scaled = build_projection(pa, games, "2026-06-30", 2026, DEFAULT_PARAMS.replace(sims=100))
    raw = build_projection(
        pa, games, "2026-06-30", 2026,
        DEFAULT_PARAMS.replace(sims=100, league_normalize=False),
    )
    order = lambda p: sorted(p.teams, key=lambda t: -p.teams[t].point_rate)
    assert order(scaled) == order(raw)


def test_league_environment_widens_intervals_without_moving_the_odds(tmp_path):
    """Weather is common to all 30 clubs: it adds spread, not a competitive edge."""
    db = tmp_path / "league.db"
    write_pitches(db, synth_league(
        hr_talent={"NYY": 0.055, "BOS": 0.035, "TOR": 0.025, "TB": 0.02}
    ))
    pa = frame(db)
    # A long horizon, so the shared factor is visible above Poisson noise.
    games = remaining_games(per_team=60)
    base = DEFAULT_PARAMS.replace(sims=4000)

    with_env = simulate(build_projection(pa, games, "2026-06-30", 2026, base))
    without = simulate(build_projection(
        pa, games, "2026-06-30", 2026, base.replace(league_env_sd=0.0)
    ))

    for team in TEAMS:
        assert with_env.draws[team].std() > without.draws[team].std()

    lead_with = with_env.totals.set_index("team")["p_lead"]
    lead_without = without.totals.set_index("team")["p_lead"]
    for team in TEAMS:
        assert lead_with[team] == pytest.approx(lead_without[team], abs=0.05)


def test_player_projections_are_coherent_with_the_team_total(projection):
    """The team's remaining home runs are its hitters', drawn once - not twice."""
    result = simulate(projection)
    players = result.players
    assert not players.empty

    by_team = players.groupby("team")["expected_remaining"].sum()
    for team in TEAMS:
        ti = projection.teams[team]
        # Same draws, so the two views agree up to Monte Carlo error only.
        assert by_team[team] == pytest.approx(
            result.draws[team].mean() - ti.hr_to_date, rel=1e-9
        )
        assert set(players[players["team"] == team]["batter"]) == set(ti.batters["batter"])


def test_player_rows_are_sane(projection):
    result = simulate(projection)
    players = result.players

    assert players["projected"].is_monotonic_decreasing        # sorted best first
    assert (players["projected"] >= players["hr_to_date"]).all()
    assert (players["p10"] <= players["median"]).all()
    assert (players["median"] <= players["p90"]).all()
    assert (players["proj_pa"] > 0).all()


def test_milestone_probabilities_are_ordered(projection):
    result = simulate(projection)
    players = result.players

    assert {"p_40", "p_50"} <= set(players.columns)
    for col in ("p_40", "p_50"):
        assert players[col].between(0, 1).all()
    # Reaching 50 is never easier than reaching 40.
    assert (players["p_40"] >= players["p_50"] - 1e-12).all()


def test_milestones_are_configurable(projection):
    from dataclasses import replace as dc_replace

    result = simulate(dc_replace(
        projection, params=projection.params.replace(hr_milestones=(10,))
    ))
    assert "p_10" in result.players.columns
    assert "p_40" not in result.players.columns


def test_a_hitter_who_has_already_cleared_the_bar_is_certain(tmp_path):
    """Home runs already hit cannot be taken away by the simulation."""
    db = tmp_path / "league.db"
    write_pitches(db, synth_league(hr_talent={t: 0.05 for t in TEAMS}))
    pa = frame(db)
    params = DEFAULT_PARAMS.replace(sims=500, hr_milestones=(1,))
    proj = build_projection(pa, remaining_games(), "2026-06-30", 2026, params)

    players = simulate(proj).players
    already = players[players["hr_to_date"] >= 1]
    assert not already.empty
    assert (already["p_1"] == 1.0).all()
