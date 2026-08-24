import json

import pytest
import responses

from hrproj.schedule import (
    SCHEDULE_URL,
    TEAMS_URL,
    fallback_remaining,
    fetch_schedule,
    last_refreshed,
    load_remaining,
    refresh_cache,
)

SCHEDULE_PAYLOAD = {
    "dates": [
        {
            "date": "2026-08-25",
            "games": [
                {   # ordinary game
                    "gamePk": 1, "status": {"detailedState": "Scheduled"},
                    "teams": {"home": {"team": {"id": 147}}, "away": {"team": {"id": 111}}},
                    "venue": {"id": 3313, "name": "Yankee Stadium"},
                },
                {   # doubleheader: same clubs, same day, second gamePk
                    "gamePk": 2, "status": {"detailedState": "Scheduled"},
                    "teams": {"home": {"team": {"id": 147}}, "away": {"team": {"id": 111}}},
                    "venue": {"id": 3313, "name": "Yankee Stadium"},
                },
                {   # postponed: will reappear when rescheduled, so it must not count
                    "gamePk": 3, "status": {"detailedState": "Postponed"},
                    "teams": {"home": {"team": {"id": 112}}, "away": {"team": {"id": 158}}},
                    "venue": {"id": 17, "name": "Wrigley Field"},
                },
                {   # already played
                    "gamePk": 4, "status": {"detailedState": "Final"},
                    "teams": {"home": {"team": {"id": 119}}, "away": {"team": {"id": 137}}},
                    "venue": {"id": 22, "name": "Dodger Stadium"},
                },
                {   # neutral site: Yankees "home" somewhere that is not their park
                    "gamePk": 5, "status": {"detailedState": "Scheduled"},
                    "teams": {"home": {"team": {"id": 147}}, "away": {"team": {"id": 141}}},
                    "venue": {"id": 9999, "name": "Field of Dreams"},
                },
            ],
        }
    ]
}

TEAMS_PAYLOAD = {
    "teams": [
        {"id": 147, "venue": {"id": 3313, "name": "Yankee Stadium"}},
        {"id": 111, "venue": {"id": 3, "name": "Fenway Park"}},
        {"id": 112, "venue": {"id": 17, "name": "Wrigley Field"}},
        {"id": 158, "venue": {"id": 32, "name": "American Family Field"}},
        {"id": 119, "venue": {"id": 22, "name": "Dodger Stadium"}},
        {"id": 137, "venue": {"id": 2395, "name": "Oracle Park"}},
        {"id": 141, "venue": {"id": 14, "name": "Rogers Centre"}},
    ]
}


def register_api():
    responses.add(responses.GET, SCHEDULE_URL, json=SCHEDULE_PAYLOAD, status=200)
    responses.add(responses.GET, TEAMS_URL, json=TEAMS_PAYLOAD, status=200)


@responses.activate
def test_fetch_schedule_maps_team_ids():
    register_api()
    games = fetch_schedule("2026-08-25", "2026-09-27", 2026)
    assert len(games) == 5
    assert games[0]["home_team"] == "NYY"
    assert games[0]["away_team"] == "BOS"


@responses.activate
def test_cached_remaining_skips_finished_and_postponed_games(tmp_path):
    register_api()
    cache = tmp_path / "cache.db"
    stored = refresh_cache(cache, "2026-08-25", "2026-09-27", 2026)
    assert stored == 5

    remaining = load_remaining(cache, 2026, "2026-08-25", "2026-09-27")
    game_pks = {m["game_pk"] for m in remaining}
    assert game_pks == {1, 2, 5}                    # Final and Postponed dropped

    nyy = [m for m in remaining if m["team"] == "NYY"]
    assert len(nyy) == 3                            # both halves of the doubleheader plus the neutral game
    assert last_refreshed(cache, 2026) is not None


@responses.activate
def test_neutral_site_games_carry_no_park(tmp_path):
    register_api()
    cache = tmp_path / "cache.db"
    refresh_cache(cache, "2026-08-25", "2026-09-27", 2026)
    remaining = load_remaining(cache, 2026, "2026-08-25", "2026-09-27")

    by_pk = {(m["game_pk"], m["team"]): m for m in remaining}
    assert by_pk[(1, "NYY")]["venue_team"] == "NYY"
    assert by_pk[(5, "NYY")]["venue_team"] is None
    assert by_pk[(1, "BOS")]["home"] is False


@responses.activate
def test_refreshing_twice_does_not_duplicate_games(tmp_path):
    register_api()
    cache = tmp_path / "cache.db"
    refresh_cache(cache, "2026-08-25", "2026-09-27", 2026)
    refresh_cache(cache, "2026-08-25", "2026-09-27", 2026)
    remaining = load_remaining(cache, 2026, "2026-08-25", "2026-09-27")
    assert len(remaining) == 6                       # 3 live games x 2 clubs


def test_offline_fallback_counts_games_to_162():
    stubs = fallback_remaining({"NYY": 130, "BOS": 132})
    per_team = {}
    for stub in stubs:
        per_team[stub["team"]] = per_team.get(stub["team"], 0) + 1

    assert per_team == {"NYY": 32, "BOS": 30}
    assert all(s["venue_team"] is None and s["opponent"] is None for s in stubs)


def test_offline_fallback_handles_a_finished_season():
    assert fallback_remaining({"NYY": 162}) == []


@responses.activate
def test_include_completed_keeps_played_games_but_not_abandoned_ones(tmp_path):
    """A projection run from a past date must still count the games played since."""
    register_api()
    cache = tmp_path / "cache.db"
    refresh_cache(cache, "2026-08-25", "2026-09-27", 2026)

    remaining = load_remaining(
        cache, 2026, "2026-08-25", "2026-09-27", include_completed=True
    )
    game_pks = {m["game_pk"] for m in remaining}
    assert game_pks == {1, 2, 4, 5}      # the Final game is back, the Postponed one is not
