"""Team identity helpers.

Baseball Savant and the MLB StatsAPI use the same 30 abbreviations, so no
translation is needed between the two data sources. FanGraphs (and most
published standings) differ for eight clubs; ``FANGRAPHS_ABBR`` exists purely so
reports line up with those tables.
"""

# StatsAPI team id -> abbreviation shared by Savant and StatsAPI.
STATSAPI_TEAM_IDS = {
    108: "LAA", 109: "AZ", 110: "BAL", 111: "BOS", 112: "CHC", 113: "CIN",
    114: "CLE", 115: "COL", 116: "DET", 117: "HOU", 118: "KC", 119: "LAD",
    120: "WSH", 121: "NYM", 133: "ATH", 134: "PIT", 135: "SD", 136: "SEA",
    137: "SF", 138: "STL", 139: "TB", 140: "TEX", 141: "TOR", 142: "MIN",
    143: "PHI", 144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY", 158: "MIL",
}

TEAMS = sorted(STATSAPI_TEAM_IDS.values())

# Only the clubs where FanGraphs' abbreviation differs from Savant's.
FANGRAPHS_ABBR = {
    "AZ": "ARI", "CWS": "CHW", "KC": "KCR", "SD": "SDP",
    "SF": "SFG", "TB": "TBR", "WSH": "WSN",
}

# SQL expression: the batting team of a pitch row.
BATTING_TEAM_SQL = "CASE WHEN inning_topbot = 'Top' THEN away_team ELSE home_team END"

# Events that appear in `events` but do not end a plate appearance.
NON_PA_EVENTS = frozenset({
    "caught_stealing_2b", "caught_stealing_3b", "caught_stealing_home",
    "pickoff_1b", "pickoff_2b", "pickoff_3b",
    "pickoff_caught_stealing_2b", "pickoff_caught_stealing_3b",
    "pickoff_caught_stealing_home", "pickoff_error_1b", "pickoff_error_2b",
    "pickoff_error_3b", "stolen_base_2b", "stolen_base_3b", "stolen_base_home",
    "wild_pitch", "passed_ball", "balk", "other_advance", "runner_double_play",
    "defensive_indiff", "game_advisory", "ejection", "cs_double_play",
    "batter_timeout", "injury", "os_ruling_pending_prior",
    # A plate appearance the game ended in the middle of - Statcast records it,
    # FanGraphs does not count it, and it never resolved into an outcome.
    "truncated_pa",
})


def fangraphs(abbr: str) -> str:
    """Return the FanGraphs-style abbreviation for a Savant/StatsAPI team code."""
    return FANGRAPHS_ABBR.get(abbr, abbr)
