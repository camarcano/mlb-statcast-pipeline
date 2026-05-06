import io
import time
import urllib.request

import pandas as pd

_CACHE: dict | None = None
_CACHE_TS: float = 0
_TTL = 3600  # 1 hour

SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1JgczhD5VDQ1EiXqVG-blttZcVwbZd5_Ne_mefUGwJnk"
    "/export?format=csv&gid=0"
)


def get_nfbc_to_mlb_mapping() -> dict[str, int]:
    global _CACHE, _CACHE_TS

    if _CACHE is not None and (time.time() - _CACHE_TS) < _TTL:
        return _CACHE

    try:
        resp = urllib.request.urlopen(SHEET_CSV_URL, timeout=15)
        df = pd.read_csv(io.BytesIO(resp.read()))
    except Exception:
        return _CACHE or {}

    col_map = {}
    for col in df.columns:
        stripped = col.strip().lower().replace(" ", "")
        if stripped in ("nfbcid", "nfbc"):
            col_map["nfbc"] = col
        elif stripped in ("mlbid", "mlb"):
            col_map["mlb"] = col

    if "nfbc" not in col_map or "mlb" not in col_map:
        return _CACHE or {}

    mapping = {}
    for _, row in df.iterrows():
        try:
            nfbc = int(row[col_map["nfbc"]])
            mlb = int(row[col_map["mlb"]])
            mapping[nfbc] = mlb
        except (ValueError, TypeError):
            continue

    _CACHE = mapping
    _CACHE_TS = time.time()
    return mapping


def map_roster_csv(csv_file) -> tuple[list[int], int]:
    nfbc_map = get_nfbc_to_mlb_mapping()
    df = pd.read_csv(csv_file)

    total = len(df)
    batter_ids = []
    for raw_id in df["id"]:
        try:
            nfbc_id = int(raw_id)
            if nfbc_id in nfbc_map:
                batter_ids.append(nfbc_map[nfbc_id])
        except (ValueError, TypeError):
            continue

    return batter_ids, total
