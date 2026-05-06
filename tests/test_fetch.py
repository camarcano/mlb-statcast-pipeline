from unittest.mock import patch

from savant.fetch import build_url, fetch_csv, parse_csv, FetchError


def test_build_url_single_game_type():
    url = build_url("2026-05-03", "2026-05-03", ["R"])
    assert "baseballsavant.mlb.com/statcast_search/csv" in url
    assert "game_date_gt=2026-05-03" in url
    assert "game_date_lt=2026-05-03" in url
    assert "player_type=batter" in url
    assert "type=details" in url
    assert "all=true" in url


def test_build_url_multiple_game_types():
    url = build_url("2026-05-03", "2026-05-03", ["S", "R", "F"])
    assert "R" in url or "S" in url


def test_build_url_default_game_type():
    url = build_url("2026-05-03", "2026-05-03")
    assert "R" in url


def test_parse_csv(mock_response_csv):
    df = parse_csv(mock_response_csv)
    assert len(df) == 1
    assert df.iloc[0]["pitch_type"] == "FF"
    assert df.iloc[0]["game_date"] == "2026-05-03"


def test_parse_csv_empty():
    from savant.db import CSV_COLUMNS
    header = ",".join(CSV_COLUMNS)
    df = parse_csv(header + "\n")
    assert len(df) == 0


@patch("savant.fetch.requests.get")
def test_fetch_csv_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "pitch_type\ngame_date\nFF\n2026-05-03\n"
    mock_get.return_value.raise_for_status = lambda: None

    result = fetch_csv("https://example.com/test")
    assert "pitch_type" in result


@patch("savant.fetch.requests.get")
def test_fetch_csv_timeout_retries(mock_get):
    import requests
    mock_get.side_effect = [
        requests.Timeout("timeout"),
        requests.Timeout("timeout"),
        type("Resp", (), {
            "status_code": 200,
            "text": "ok",
            "raise_for_status": lambda self: None,
        })(),
    ]

    with patch("savant.fetch.get_max_retries", return_value=3):
        result = fetch_csv("https://example.com/test")
    assert result == "ok"


@patch("savant.fetch.requests.get")
def test_fetch_csv_exhausts_retries(mock_get):
    import requests
    mock_get.side_effect = requests.Timeout("timeout")

    with patch("savant.fetch.get_max_retries", return_value=2):
        try:
            fetch_csv("https://example.com/test")
            assert False, "Should have raised FetchError"
        except FetchError:
            pass
