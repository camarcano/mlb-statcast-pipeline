import io
import logging
import time
from typing import Optional

import pandas as pd
import requests

from savant.config import get_max_retries, get_rate_limit, get_request_timeout

logger = logging.getLogger(__name__)

BASE_URL = "https://baseballsavant.mlb.com/statcast_search/csv"

GAME_TYPES = {
    "S": "Spring Training",
    "R": "Regular Season",
    "F": "Wild Card",
    "D": "Division Series",
    "L": "LCS",
    "W": "World Series",
}

RETRY_BACKOFF = [2, 5, 15]


class FetchError(Exception):
    pass


def build_url(
    game_date_start: str,
    game_date_end: str,
    game_types: Optional[list[str]] = None,
) -> str:
    if game_types is None:
        game_types = ["R"]

    gt_param = "|".join(game_types) + "|"

    params = {
        "all": "true",
        "hfGT": gt_param,
        "type": "details",
        "player_type": "batter",
        "game_date_gt": game_date_start,
        "game_date_lt": game_date_end,
    }

    req = requests.Request("GET", BASE_URL, params=params).prepare()
    return req.url


def fetch_csv(url: str) -> str:
    max_retries = get_max_retries()
    timeout = get_request_timeout()
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "mlb-statcast-pipeline/0.1.0"},
            )
            resp.raise_for_status()
            return resp.text

        except requests.Timeout as e:
            last_error = e
            logger.warning("Timeout on attempt %d/%d", attempt + 1, max_retries)

        except requests.HTTPError as e:
            if resp.status_code == 429:
                wait = 60
                logger.warning("Rate limited, waiting %ds", wait)
            elif resp.status_code >= 500:
                wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                logger.warning(
                    "Server error %d, retry in %ds", resp.status_code, wait
                )
            else:
                raise FetchError(
                    f"HTTP {resp.status_code} (non-retryable): {resp.text[:200]}"
                ) from e
            time.sleep(wait)
            continue

        except requests.ConnectionError as e:
            last_error = e
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            logger.warning("Connection error, retry in %ds", wait)
            time.sleep(wait)
            continue

    raise FetchError(f"Failed after {max_retries} retries: {last_error}")


def parse_csv(csv_text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text), low_memory=False)

    if df.empty:
        return df

    df["game_date"] = pd.to_datetime(df["game_date"]).dt.strftime("%Y-%m-%d")

    if "game_year" not in df.columns:
        df["game_year"] = pd.to_datetime(df["game_date"]).dt.year

    return df


def fetch_date(
    game_date: str,
    game_types: Optional[list[str]] = None,
) -> pd.DataFrame:
    if game_types is None:
        game_types = list(GAME_TYPES.keys())

    url = build_url(game_date, game_date, game_types)
    logger.info("Fetching %s (types: %s)", game_date, ",".join(game_types))

    start = time.time()
    csv_text = fetch_csv(url)
    elapsed = time.time() - start

    df = parse_csv(csv_text)
    logger.info(
        "Fetched %s: %d rows in %.1fs", game_date, len(df), elapsed
    )

    if len(df) == 25000:
        logger.warning(
            "Received exactly 25,000 rows for %s - data may be truncated!",
            game_date,
        )

    return df


def rate_limit_pause() -> None:
    delay = get_rate_limit()
    time.sleep(delay)
