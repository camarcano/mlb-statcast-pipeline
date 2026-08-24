"""Synthetic Statcast databases for testing.

Rows go in through the pipeline's own `init_db` / `insert_pitches`, so the tests
exercise the real schema rather than a hand-rolled stand-in.
"""

import numpy as np
import pandas as pd
import pytest

from savant.db import CSV_COLUMNS, init_db, insert_pitches

REQUIRED_DEFAULTS = {
    "game_date": "2026-04-01",
    "batter": 100001,
    "pitcher": 200001,
    "game_type": "R",
    "home_team": "NYY",
    "away_team": "BOS",
    "game_year": 2026,
    "game_pk": 700001,
    "at_bat_number": 1,
    "pitch_number": 1,
    "inning_topbot": "Top",
    "stand": "R",
    "type": "S",
    "events": "strikeout",
    "player_name": "Test, Batter",
}


def make_pitch(**overrides) -> dict:
    row = {col: None for col in CSV_COLUMNS}
    row.update(REQUIRED_DEFAULTS)
    row.update(overrides)
    return row


def write_pitches(db_path, rows) -> None:
    init_db(db_path)
    insert_pitches(pd.DataFrame(rows), db_path=db_path)


@pytest.fixture
def empty_db(tmp_path):
    db_path = tmp_path / "statcast.db"
    init_db(db_path)
    return db_path


def synth_league(
    teams=("NYY", "BOS", "TOR", "TB"),
    games_per_matchup=12,
    batters_per_team=9,
    start_date="2026-04-01",
    seed=7,
    hr_talent=None,
):
    """A miniature season: every team plays every other team, nine hitters each.

    `hr_talent` maps team -> HR probability per plate appearance, letting a test
    make one club genuinely better at hitting home runs.
    """
    rng = np.random.default_rng(seed)
    hr_talent = hr_talent or {t: 0.035 for t in teams}
    start = pd.Timestamp(start_date)

    matchups = [(home, away) for i, home in enumerate(teams) for away in teams[i + 1:]]

    rows = []
    game_pk = 700000
    day = 0
    # The round robin is interleaved so every club plays across the whole span,
    # rather than one team's entire schedule finishing before another's begins.
    for _ in range(games_per_matchup):
        for home, away in matchups:
            game_pk += 1
            date = (start + pd.Timedelta(days=day)).date().isoformat()
            day += 1
            for half, (team, topbot) in enumerate(((away, "Top"), (home, "Bot"))):
                for slot in range(batters_per_team):
                    batter = 100000 + teams.index(team) * 100 + slot
                    for pa_n in range(4):
                        is_hr = rng.random() < hr_talent[team]
                        in_play = is_hr or rng.random() < 0.65
                        rows.append(make_pitch(
                            game_date=date,
                            game_pk=game_pk,
                            home_team=home,
                            away_team=away,
                            inning_topbot=topbot,
                            batter=batter,
                            pitcher=200000 + teams.index(home if topbot == "Top" else away),
                            player_name=f"{team}, Hitter{slot}",
                            stand="R" if slot % 2 == 0 else "L",
                            at_bat_number=half * 100 + slot * 4 + pa_n + 1,
                            pitch_number=1,
                            type="X" if in_play else "S",
                            events="home_run" if is_hr else ("field_out" if in_play else "strikeout"),
                            launch_speed=float(rng.normal(103 if is_hr else 88, 5)) if in_play else None,
                            launch_angle=float(rng.normal(28 if is_hr else 8, 6)) if in_play else None,
                            hc_x=float(rng.normal(125, 40)) if in_play else None,
                            hc_y=float(rng.normal(120, 30)) if in_play else None,
                        ))
    return rows


@pytest.fixture
def league_db(tmp_path):
    db_path = tmp_path / "league.db"
    write_pitches(db_path, synth_league())
    return db_path
