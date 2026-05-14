import json
import os

_cache = None
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "batter_info.json")


def load_batter_info() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache

    if not os.path.exists(_CACHE_PATH):
        _cache = {}
        return _cache

    with open(_CACHE_PATH) as f:
        _cache = json.load(f)
    return _cache


def get_batter_position(batter_id: int) -> str:
    info = load_batter_info()
    entry = info.get(str(batter_id))
    return entry["position"] if entry else ""


def enrich_with_positions(records: list[dict]) -> list[dict]:
    info = load_batter_info()
    for r in records:
        bid = r.get("batter")
        if bid is not None:
            entry = info.get(str(bid))
            r["position"] = entry["position"] if entry else ""
    return records
