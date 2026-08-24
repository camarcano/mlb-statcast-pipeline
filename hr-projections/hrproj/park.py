"""Park home run factors, from the season's own batted balls.

Measured on air contact (10-50 degrees) rather than all batted balls, so a park's
factor is not diluted by ground balls no wall placement can affect. A single
season of one park's data is noisy, hence the shrinkage - and `--no-park` exists
for anyone who would rather not carry the assumption at all.
"""

import pandas as pd

from hrproj.config import ModelParams


def park_factors(pa: pd.DataFrame, params: ModelParams) -> pd.Series:
    """HR-per-air-ball at each park relative to league, shrunk toward 1.0.

    Indexed by the home club's abbreviation (its park). Missing parks read as 1.0.
    """
    air = pa[pa["is_air"]]
    if air.empty:
        return pd.Series(dtype=float)

    league_rate = float(air["is_hr"].mean())
    if league_rate <= 0:
        return pd.Series(1.0, index=sorted(air["venue"].unique()))

    grouped = air.groupby("venue")["is_hr"]
    n = grouped.size()
    raw = grouped.mean() / league_rate
    weight = n / (n + params.park_n0)
    return 1.0 + weight * (raw - 1.0)


def opponent_factors(
    pa: pd.DataFrame, parks: pd.Series, params: ModelParams
) -> pd.Series:
    """Each club's staff HR-allowed rate relative to league, park-neutralised.

    Every air ball allowed is compared against what the league would have hit in
    that same park, so a staff is not credited for pitching half its games in a
    pitcher's park.
    """
    air = pa[pa["is_air"]]
    if air.empty:
        return pd.Series(dtype=float)

    league_rate = float(air["is_hr"].mean())
    if league_rate <= 0:
        return pd.Series(1.0, index=sorted(air["pitch_team"].unique()))

    park_of_game = air["venue"].map(parks).fillna(1.0)
    expected = league_rate * park_of_game

    allowed = air.groupby("pitch_team")["is_hr"].sum()
    expected_by_team = expected.groupby(air["pitch_team"]).sum()
    n = air.groupby("pitch_team").size()

    raw = allowed / expected_by_team.replace(0, pd.NA)
    raw = raw.astype(float).fillna(1.0)
    weight = n / (n + params.opp_n0)
    return 1.0 + weight * (raw - 1.0)
