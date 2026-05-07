import json
import os

_cache = None
_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pitcher_names.json")


def load_pitcher_names() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache

    if not os.path.exists(_CACHE_PATH):
        _cache = {}
        return _cache

    with open(_CACHE_PATH) as f:
        _cache = json.load(f)
    return _cache


def get_pitcher_name(pitcher_id: int) -> str:
    names = load_pitcher_names()
    return names.get(str(pitcher_id), f"Pitcher {pitcher_id}")


def resolve_names(records: list[dict]) -> list[dict]:
    names = load_pitcher_names()
    for r in records:
        pid = r.get("pitcher")
        if pid is not None:
            r["player_name"] = names.get(str(pid), r.get("player_name", f"Pitcher {pid}"))
    return records
