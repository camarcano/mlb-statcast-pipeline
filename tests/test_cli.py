from unittest.mock import patch, MagicMock
from contextlib import contextmanager

import pandas as pd
from click.testing import CliRunner

from savant.cli import cli


@contextmanager
def patch_db_path(db_path):
    """Patch get_db_path in all modules that import it."""
    with (
        patch("savant.cli.get_db_path", return_value=db_path),
        patch("savant.db.get_db_path", return_value=db_path),
    ):
        yield


def test_init_command(tmp_path):
    runner = CliRunner()
    with patch_db_path(tmp_path / "test.db"):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Database initialized" in result.output


def test_status_empty(tmp_path):
    db_path = tmp_path / "test.db"
    from savant.db import init_db
    init_db(db_path)

    runner = CliRunner()
    with patch_db_path(db_path):
        result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0


def test_status_no_db(tmp_path):
    runner = CliRunner()
    with patch_db_path(tmp_path / "nonexistent.db"):
        result = runner.invoke(cli, ["status"])
    assert "not found" in result.output


def test_verify_no_db(tmp_path):
    runner = CliRunner()
    with patch_db_path(tmp_path / "nonexistent.db"):
        result = runner.invoke(cli, ["verify"])
    assert "not found" in result.output


@patch("savant.cli.fetch_date")
@patch("savant.cli.rate_limit_pause")
def test_update_command(mock_pause, mock_fetch, tmp_path, sample_df):
    db_path = tmp_path / "test.db"
    from savant.db import init_db
    init_db(db_path)

    mock_fetch.return_value = sample_df

    runner = CliRunner()
    with patch_db_path(db_path):
        result = runner.invoke(cli, ["update", "--date", "2026-05-03"])
    assert result.exit_code == 0
    assert "rows inserted" in result.output
