import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_path() -> Path:
    raw = os.getenv("SAVANT_DB_PATH", "data/savant.db")
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def get_log_dir() -> Path:
    raw = os.getenv("SAVANT_LOG_DIR", "logs")
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def get_log_level() -> str:
    return os.getenv("SAVANT_LOG_LEVEL", "INFO")


def get_rate_limit() -> float:
    return float(os.getenv("SAVANT_RATE_LIMIT", "1.5"))


def get_max_retries() -> int:
    return int(os.getenv("SAVANT_MAX_RETRIES", "3"))


def get_request_timeout() -> int:
    return int(os.getenv("SAVANT_REQUEST_TIMEOUT", "120"))
