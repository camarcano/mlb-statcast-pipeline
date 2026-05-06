import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from savant.config import get_db_path

# All 118 columns from the Baseball Savant CSV, in order.
# These must match the CSV headers exactly for INSERT alignment.
CSV_COLUMNS = [
    "pitch_type", "game_date", "release_speed", "release_pos_x", "release_pos_z",
    "player_name", "batter", "pitcher", "events", "description",
    "spin_dir", "spin_rate_deprecated", "break_angle_deprecated", "break_length_deprecated",
    "zone", "des", "game_type", "stand", "p_throws", "home_team", "away_team",
    "type", "hit_location", "bb_type", "balls", "strikes", "game_year",
    "pfx_x", "pfx_z", "plate_x", "plate_z", "on_3b", "on_2b", "on_1b",
    "outs_when_up", "inning", "inning_topbot", "hc_x", "hc_y",
    "tfs_deprecated", "tfs_zulu_deprecated", "umpire", "sv_id",
    "vx0", "vy0", "vz0", "ax", "ay", "az",
    "sz_top", "sz_bot", "hit_distance_sc", "launch_speed", "launch_angle",
    "effective_speed", "release_spin_rate", "release_extension", "game_pk",
    "fielder_2", "fielder_3", "fielder_4", "fielder_5", "fielder_6",
    "fielder_7", "fielder_8", "fielder_9", "release_pos_y",
    "estimated_ba_using_speedangle", "estimated_woba_using_speedangle",
    "woba_value", "woba_denom", "babip_value", "iso_value",
    "launch_speed_angle", "at_bat_number", "pitch_number", "pitch_name",
    "home_score", "away_score", "bat_score", "fld_score",
    "post_away_score", "post_home_score", "post_bat_score", "post_fld_score",
    "if_fielding_alignment", "of_fielding_alignment", "spin_axis",
    "delta_home_win_exp", "delta_run_exp", "bat_speed", "swing_length",
    "estimated_slg_using_speedangle", "delta_pitcher_run_exp", "hyper_speed",
    "home_score_diff", "bat_score_diff", "home_win_exp", "bat_win_exp",
    "age_pit_legacy", "age_bat_legacy", "age_pit", "age_bat",
    "n_thruorder_pitcher", "n_priorpa_thisgame_player_at_bat",
    "pitcher_days_since_prev_game", "batter_days_since_prev_game",
    "pitcher_days_until_next_game", "batter_days_until_next_game",
    "api_break_z_with_gravity", "api_break_x_arm", "api_break_x_batter_in",
    "arm_angle", "attack_angle", "attack_direction", "swing_path_tilt",
    "intercept_ball_minus_batter_pos_x_inches",
    "intercept_ball_minus_batter_pos_y_inches",
]

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS statcast_pitches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pitch_type TEXT,
    game_date TEXT NOT NULL,
    release_speed REAL,
    release_pos_x REAL,
    release_pos_z REAL,
    player_name TEXT,
    batter INTEGER NOT NULL,
    pitcher INTEGER NOT NULL,
    events TEXT,
    description TEXT,
    spin_dir REAL,
    spin_rate_deprecated REAL,
    break_angle_deprecated REAL,
    break_length_deprecated REAL,
    zone INTEGER,
    des TEXT,
    game_type TEXT NOT NULL,
    stand TEXT,
    p_throws TEXT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    type TEXT,
    hit_location INTEGER,
    bb_type TEXT,
    balls INTEGER,
    strikes INTEGER,
    game_year INTEGER NOT NULL,
    pfx_x REAL,
    pfx_z REAL,
    plate_x REAL,
    plate_z REAL,
    on_3b INTEGER,
    on_2b INTEGER,
    on_1b INTEGER,
    outs_when_up INTEGER,
    inning INTEGER,
    inning_topbot TEXT,
    hc_x REAL,
    hc_y REAL,
    tfs_deprecated TEXT,
    tfs_zulu_deprecated TEXT,
    umpire TEXT,
    sv_id TEXT,
    vx0 REAL,
    vy0 REAL,
    vz0 REAL,
    ax REAL,
    ay REAL,
    az REAL,
    sz_top REAL,
    sz_bot REAL,
    hit_distance_sc INTEGER,
    launch_speed REAL,
    launch_angle REAL,
    effective_speed REAL,
    release_spin_rate INTEGER,
    release_extension REAL,
    game_pk INTEGER NOT NULL,
    fielder_2 INTEGER,
    fielder_3 INTEGER,
    fielder_4 INTEGER,
    fielder_5 INTEGER,
    fielder_6 INTEGER,
    fielder_7 INTEGER,
    fielder_8 INTEGER,
    fielder_9 INTEGER,
    release_pos_y REAL,
    estimated_ba_using_speedangle REAL,
    estimated_woba_using_speedangle REAL,
    woba_value REAL,
    woba_denom REAL,
    babip_value REAL,
    iso_value REAL,
    launch_speed_angle INTEGER,
    at_bat_number INTEGER NOT NULL,
    pitch_number INTEGER NOT NULL,
    pitch_name TEXT,
    home_score INTEGER,
    away_score INTEGER,
    bat_score INTEGER,
    fld_score INTEGER,
    post_away_score INTEGER,
    post_home_score INTEGER,
    post_bat_score INTEGER,
    post_fld_score INTEGER,
    if_fielding_alignment TEXT,
    of_fielding_alignment TEXT,
    spin_axis REAL,
    delta_home_win_exp REAL,
    delta_run_exp REAL,
    bat_speed REAL,
    swing_length REAL,
    estimated_slg_using_speedangle REAL,
    delta_pitcher_run_exp REAL,
    hyper_speed REAL,
    home_score_diff INTEGER,
    bat_score_diff INTEGER,
    home_win_exp REAL,
    bat_win_exp REAL,
    age_pit_legacy INTEGER,
    age_bat_legacy INTEGER,
    age_pit INTEGER,
    age_bat INTEGER,
    n_thruorder_pitcher INTEGER,
    n_priorpa_thisgame_player_at_bat INTEGER,
    pitcher_days_since_prev_game INTEGER,
    batter_days_since_prev_game INTEGER,
    pitcher_days_until_next_game INTEGER,
    batter_days_until_next_game INTEGER,
    api_break_z_with_gravity REAL,
    api_break_x_arm REAL,
    api_break_x_batter_in REAL,
    arm_angle REAL,
    attack_angle REAL,
    attack_direction REAL,
    swing_path_tilt REAL,
    intercept_ball_minus_batter_pos_x_inches REAL,
    intercept_ball_minus_batter_pos_y_inches REAL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(game_pk, at_bat_number, pitch_number)
);

CREATE INDEX IF NOT EXISTS idx_pitches_game_date ON statcast_pitches(game_date);
CREATE INDEX IF NOT EXISTS idx_pitches_game_type_date ON statcast_pitches(game_type, game_date);
CREATE INDEX IF NOT EXISTS idx_pitches_batter ON statcast_pitches(batter, game_date);
CREATE INDEX IF NOT EXISTS idx_pitches_pitcher ON statcast_pitches(pitcher, game_date);
CREATE INDEX IF NOT EXISTS idx_pitches_game_pk ON statcast_pitches(game_pk);
CREATE INDEX IF NOT EXISTS idx_pitches_home_team ON statcast_pitches(home_team, game_date);
CREATE INDEX IF NOT EXISTS idx_pitches_away_team ON statcast_pitches(away_team, game_date);

CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    game_type TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    fetch_status TEXT NOT NULL DEFAULT 'pending',
    last_fetch_ts TEXT NOT NULL,
    error_message TEXT,
    elapsed_seconds REAL,
    UNIQUE(game_date, game_type)
);

CREATE INDEX IF NOT EXISTS idx_fetchlog_date ON fetch_log(game_date);
CREATE INDEX IF NOT EXISTS idx_fetchlog_status ON fetch_log(fetch_status);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);
"""

PLACEHOLDERS = ", ".join(["?"] * len(CSV_COLUMNS))
INSERT_SQL = (
    f"INSERT OR IGNORE INTO statcast_pitches ({', '.join(CSV_COLUMNS)}) "
    f"VALUES ({PLACEHOLDERS})"
)


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_V1)
        existing = conn.execute(
            "SELECT 1 FROM schema_version WHERE version = 1"
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (1, 'Initial schema')"
            )
        conn.commit()
    finally:
        conn.close()


def insert_pitches(df: pd.DataFrame, db_path: Optional[Path] = None) -> int:
    if df.empty:
        return 0

    df = df.reindex(columns=CSV_COLUMNS)
    rows = df.where(df.notna(), None).values.tolist()

    conn = get_connection(db_path)
    try:
        before = conn.execute("SELECT COUNT(*) FROM statcast_pitches").fetchone()[0]
        conn.executemany(INSERT_SQL, rows)
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM statcast_pitches").fetchone()[0]
        return after - before
    finally:
        conn.close()


def upsert_fetch_log(
    game_date: str,
    game_type: str,
    row_count: int,
    fetch_status: str,
    elapsed_seconds: float,
    error_message: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO fetch_log
               (game_date, game_type, row_count, fetch_status, last_fetch_ts, elapsed_seconds, error_message)
               VALUES (?, ?, ?, ?, datetime('now'), ?, ?)""",
            (game_date, game_type, row_count, fetch_status, elapsed_seconds, error_message),
        )
        conn.commit()
    finally:
        conn.close()


def get_fetch_log(
    game_date: str, game_type: str, db_path: Optional[Path] = None
) -> Optional[dict]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM fetch_log WHERE game_date = ? AND game_type = ?",
            (game_date, game_type),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_pitch_count_for_date(
    game_date: str, game_type: Optional[str] = None, db_path: Optional[Path] = None
) -> int:
    conn = get_connection(db_path)
    try:
        if game_type:
            row = conn.execute(
                "SELECT COUNT(*) FROM statcast_pitches WHERE game_date = ? AND game_type = ?",
                (game_date, game_type),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM statcast_pitches WHERE game_date = ?",
                (game_date,),
            ).fetchone()
        return row[0]
    finally:
        conn.close()
