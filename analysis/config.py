"""Central configuration for the pitch-homogeneity study.

Every threshold, seed, taxonomy mapping and confounder date used anywhere in
the analysis lives here so that results are reproducible from one file.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = REPO_ROOT / "analysis"

# An alternate run (e.g. the in-season 2026 check) writes to suffixed
# directories so it never overwrites the headline five-season results.
_TAG = os.environ.get("ANALYSIS_TAG", "")
_SUFFIX = f"_{_TAG}" if _TAG else ""
PARQUET_DIR = REPO_ROOT / "data" / f"analysis{_SUFFIX}"
RESULTS_DIR = ANALYSIS_DIR / f"results{_SUFFIX}"
FIGURES_DIR = ANALYSIS_DIR / f"figures{_SUFFIX}"
REPORT_DIR = ANALYSIS_DIR / "report"
DB_PATH = REPO_ROOT / "data" / "savant.db"

for _d in (PARQUET_DIR, RESULTS_DIR, FIGURES_DIR, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 42
YEARS = ([int(y) for y in os.environ["ANALYSIS_YEARS"].split(",")]
         if os.environ.get("ANALYSIS_YEARS")
         else [2021, 2022, 2023, 2024, 2025])
BASE_YEAR = YEARS[0]
FINAL_YEAR = YEARS[-1]

# When the last season is still in progress, every season is truncated at this
# calendar day (MM-DD) so cross-season comparisons cover identical windows.
# Without it, "2026 vs 2025" would confound the season with the calendar.
SEASON_CUTOFF_MD = os.environ.get("SEASON_CUTOFF_MD") or None

# --- sample-size thresholds -------------------------------------------------
MIN_PITCHES_ARSENAL = 100      # pitcher-family-year rows entering shape analyses
MIN_PITCHES_ARSENAL_SENS = 200  # sensitivity threshold
MIN_PITCHES_PITCHER_YEAR = 500  # pitcher-year rows for usage-entropy analyses
MIN_PITCHES_DIRECTIONAL = 200   # repeat-pitcher directional convergence
MIN_CELL_PITCHES = 500          # shape cells retained in the scarcity panel
MIN_BATTER_TRAILING = 400       # batter-season pitches for familiarity study

BOOT_REPS = 2000
FDR_Q = 0.10
KNN_K = 25            # neighbours for kNN-density uniqueness
NN_K_CONVERGENCE = 10  # neighbours for convergence distance

# --- confounders ------------------------------------------------------------
STICKY_STUFF_DATE = "2021-06-21"  # foreign-substance enforcement began
PITCH_CLOCK_YEAR = 2023           # pitch clock + shift ban
BAT_TRACKING_FIRST_YEAR = 2023    # bat_speed / swing_length coverage starts

# --- pitch taxonomy ---------------------------------------------------------
# Savant pitch_type codes collapsed into stable families. Families are the
# primary unit of analysis because Savant's fine-grained labels drift across
# seasons (notably the 2023 introduction of ST/SV out of the SL bucket).
PITCH_FAMILIES = {
    "FF": "FF",                                    # four-seam
    "SI": "SI", "FT": "SI",                        # sinker / two-seam
    "FC": "FC",                                    # cutter
    "SL": "SLV", "ST": "SLV", "SV": "SLV",         # slider / sweeper / slurve
    "CU": "CU", "KC": "CU", "CS": "CU",            # curveball family
    "CH": "CH",                                    # changeup
    "FS": "FS", "FO": "FS",                        # splitter / forkball
}
FAMILY_LABELS = {
    "FF": "Four-seam",
    "SI": "Sinker",
    "FC": "Cutter",
    "SLV": "Slider/Sweeper",
    "CU": "Curveball",
    "CH": "Changeup",
    "FS": "Splitter",
}
FAMILY_ORDER = ["FF", "SI", "FC", "SLV", "CU", "CH", "FS"]
# Excluded: KN (knuckleball), EP (eephus), PO/FA (pitchouts, unclassified).

# --- feature space ----------------------------------------------------------
# The pitch-shape vector. arm_angle is appended at runtime only if
# 00_validate_data.py finds adequate coverage in every season.
SHAPE_FEATURES = [
    "release_speed",
    "ivb",
    "hb_arm",
    "release_spin_rate",
    "release_extension",
    "release_pos_z",
    "release_side_arm",
]
ARM_ANGLE_COVERAGE_MIN = 0.95  # fraction of pitches per season needed to include

FEATURE_LABELS = {
    "release_speed": "Velocity (mph)",
    "ivb": "Induced vertical break (in)",
    "hb_arm": "Horizontal break, arm-side (in)",
    "release_spin_rate": "Spin rate (rpm)",
    "release_extension": "Extension (ft)",
    "release_pos_z": "Release height (ft)",
    "release_side_arm": "Release side, arm-side (ft)",
    "arm_angle": "Arm angle (deg)",
}

# --- shape-cell discretisation (S6 scarcity panel, S7 exposure) -------------
CELL_VELO_BIN = 2.0   # mph
CELL_IVB_BIN = 4.0    # inches
CELL_HB_BIN = 4.0     # inches

# --- familiarity windows (S7) ----------------------------------------------
EXPOSURE_WINDOW_DAYS = 30
EXPOSURE_WINDOW_SENSITIVITY = [15, 60]

# --- columns pulled from SQLite into parquet --------------------------------
EXTRACT_COLUMNS = [
    "game_pk", "game_date", "game_year", "at_bat_number", "pitch_number",
    "pitcher", "batter", "player_name", "p_throws", "stand",
    "pitch_type", "pitch_name",
    "release_speed", "effective_speed", "release_spin_rate", "spin_axis",
    "pfx_x", "pfx_z", "plate_x", "plate_z", "zone",
    "release_pos_x", "release_pos_z", "release_extension", "arm_angle",
    "api_break_z_with_gravity", "api_break_x_arm",
    "balls", "strikes", "outs_when_up", "inning", "n_thruorder_pitcher",
    "type", "description", "events", "bb_type",
    "launch_speed", "launch_angle",
    "estimated_woba_using_speedangle", "estimated_ba_using_speedangle",
    "woba_value", "woba_denom",
    "delta_run_exp", "delta_pitcher_run_exp",
    "bat_speed", "swing_length",
    "sz_top", "sz_bot",
]

# --- outcome event sets (mirrors webapp CSW/whiff conventions) --------------
WHIFF_DESCRIPTIONS = {
    "swinging_strike", "swinging_strike_blocked", "missed_bunt",
}
SWING_DESCRIPTIONS = WHIFF_DESCRIPTIONS | {
    "foul", "foul_tip", "foul_bunt", "hit_into_play", "bunt_foul_tip",
}
CALLED_STRIKE_DESCRIPTIONS = {"called_strike"}

# Pitchers missing from data/pitcher_names.json (retired before the webapp
# roster was built), resolved once against the MLB Stats API.
EXTRA_PITCHER_NAMES = {
    542882: "Andriese, Matt",
    491624: "Valdez, C\u00e9sar",
    # corrections to the roster file, verified against the MLB Stats API
    656550: "Holmes, Grant",
    605280: "Holmes, Clay",
}
