import numpy as np
import pandas as pd
import pytest

from hrproj.config import DEFAULT_PARAMS
from hrproj.playing_time import LINEUP_SLOTS, batter_shares, cap_shares, team_pa_per_game


def test_cap_shares_normalises_and_respects_the_cap():
    cap = DEFAULT_PARAMS.share_cap_mult / LINEUP_SLOTS
    shares = cap_shares(np.array([500.0, 40, 30, 20, 10, 5, 3, 2, 1, 1]), cap)
    assert shares.sum() == pytest.approx(1.0)
    assert shares.max() <= cap + 1e-9


def test_cap_shares_leaves_reasonable_distributions_alone():
    cap = DEFAULT_PARAMS.share_cap_mult / LINEUP_SLOTS
    even = np.full(9, 100.0)
    assert cap_shares(even, cap) == pytest.approx(np.full(9, 1 / 9))


def test_cap_shares_handles_short_rosters():
    """With fewer players than the cap can cover, shares stay proportional."""
    shares = cap_shares(np.array([2.0, 1.0]), DEFAULT_PARAMS.share_cap_mult / LINEUP_SLOTS)
    assert shares == pytest.approx([2 / 3, 1 / 3])


def _pa_frame(rows):
    df = pd.DataFrame(rows)
    df["game_date"] = pd.to_datetime(df["game_date"])
    return df


def test_inactive_hitters_drop_out_of_the_shares():
    rows = []
    for day in range(1, 21):
        date = f"2026-08-{day:02d}"
        rows.append({"bat_team": "NYY", "batter": 1, "game_date": date, "game_pk": day})
        if day <= 5:                      # hurt in early August
            rows.append({"bat_team": "NYY", "batter": 2, "game_date": date, "game_pk": day})

    shares = batter_shares(_pa_frame(rows), "2026-08-20", DEFAULT_PARAMS)
    assert set(shares["batter"]) == {1}
    assert shares["share"].sum() == pytest.approx(1.0)


def test_recent_usage_outweighs_older_usage():
    rows = []
    for day in range(1, 29):
        date = f"2026-08-{day:02d}"
        # Batter 1 plays throughout; batter 2 only in the last week.
        rows.append({"bat_team": "NYY", "batter": 1, "game_date": date, "game_pk": day})
        if day > 21:
            for _ in range(3):
                rows.append({"bat_team": "NYY", "batter": 2, "game_date": date, "game_pk": day})

    shares = batter_shares(_pa_frame(rows), "2026-08-28", DEFAULT_PARAMS).set_index("batter")
    assert shares.loc[2, "share"] > shares.loc[1, "share"]


def test_team_pa_per_game_shrinks_toward_the_league(league_db):
    import sqlite3
    from hrproj.data import load_pa_frame

    conn = sqlite3.connect(league_db)
    pa = load_pa_frame(conn, 2026, "2026-01-01", "2026-12-31")
    conn.close()

    rates = team_pa_per_game(pa, DEFAULT_PARAMS)
    raw = pa.groupby("bat_team").size() / pa.groupby("bat_team")["game_pk"].nunique()
    league = len(pa) / pa["game_pk"].nunique() / 2

    # every shrunk rate sits between its raw rate and the league rate
    for team in rates.index:
        lo, hi = sorted([raw[team], league])
        assert lo - 1e-6 <= rates[team] <= hi + 1e-6
