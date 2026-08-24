"""One command to set the projections up and run them, on Windows, macOS or Linux.

Run this with any Python 3.10+; it uses only the standard library. It creates a
virtual environment next to the repository, installs the pipeline and this
project into it, backfills the season the first time, and then produces the
projection - so the everyday case is "double-click run.bat and read the table".

    python tools/bootstrap.py run      # set up if needed, update data, project
    python tools/bootstrap.py setup    # just the setup and first backfill
"""

import argparse
import os
import platform
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent      # hr-projections/
REPO_ROOT = PROJECT_DIR.parent                            # the pipeline checkout
VENV_DIR = REPO_ROOT / ".venv"
IS_WINDOWS = platform.system() == "Windows"
MIN_PYTHON = (3, 10)


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    printable = " ".join(str(c) for c in cmd)
    print(f"  $ {printable}", flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def capture(cmd) -> str:
    result = subprocess.run(
        [str(c) for c in cmd], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        sys.exit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required; "
            f"this is {platform.python_version()}.\n"
            "Install a current Python from https://www.python.org/downloads/ "
            '(tick "Add python.exe to PATH" on Windows) and try again.'
        )


def ensure_venv() -> Path:
    python = venv_python()
    if not python.exists():
        print(f"Creating a virtual environment in {VENV_DIR} ...")
        run([sys.executable, "-m", "venv", VENV_DIR])
    return python


def is_installed(python: Path) -> bool:
    result = subprocess.run(
        [str(python), "-c", "import hrproj, savant, numpy, pandas"],
        capture_output=True,
    )
    return result.returncode == 0


def install(python: Path, force: bool = False) -> None:
    if not force and is_installed(python):
        return

    print("Installing the pipeline and the projection package (a minute or two) ...")
    run([python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    # The pipeline comes from this checkout, not from git: it is right here, and a
    # local install means edits to either project take effect immediately.
    run([python, "-m", "pip", "install", "-e", REPO_ROOT, "--quiet"])
    run([python, "-m", "pip", "install", "-e", PROJECT_DIR, "--no-deps", "--quiet"])
    run([python, "-m", "pip", "install", "numpy", "--quiet"])

    if not is_installed(python):
        sys.exit("Installation finished but the packages will not import. See the log above.")


def project_settings(python: Path) -> dict:
    """Ask the installed package where things live, so there is one source of truth."""
    script = (
        "from hrproj.config import get_statcast_db, get_season, season_opening_date;"
        "print(get_statcast_db());print(get_season());print(season_opening_date())"
    )
    db_path, season, opening = capture([python, "-c", script]).splitlines()
    return {"db": Path(db_path), "season": int(season), "opening": opening}


def season_row_count(db: Path, season: int) -> int:
    if not db.exists():
        return 0
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM statcast_pitches WHERE game_type = 'R' AND game_year = ?",
            (season,),
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0        # no table yet
    finally:
        conn.close()


def backfill(python: Path, settings: dict) -> None:
    print(
        f"\nNo {settings['season']} data found in {settings['db']}.\n"
        "Downloading the season from Baseball Savant. This runs once and takes\n"
        "roughly 15-20 minutes; later runs only fetch the days since you last ran it.\n"
    )
    # The pipeline picks its database from SAVANT_DB_PATH, this project from
    # HRPROJ_STATCAST_DB. Pass the resolved path down so the two cannot disagree
    # about where the season is being stored.
    env = dict(os.environ, SAVANT_DB_PATH=str(settings["db"]))
    run([
        python, "-m", "savant.cli", "backfill",
        "--start-date", settings["opening"],
        "--game-types", "R",
    ], env=env)


def open_file(path: Path) -> None:
    try:
        if IS_WINDOWS:
            os.startfile(str(path))          # noqa: S606 - the Windows way to open a file
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:                  # noqa: BLE001 - opening a browser is a nicety
        print(f"(Could not open the report automatically: {exc})")


def newest_report(out_dir: Path) -> "Path | None":
    reports = sorted(out_dir.glob("hr_projection_*.html"))
    return reports[-1] if reports else None


def do_setup(args) -> dict:
    check_python_version()
    python = ensure_venv()
    install(python, force=args.reinstall)
    settings = project_settings(python)

    if season_row_count(settings["db"], settings["season"]) == 0:
        backfill(python, settings)

    return {"python": python, "settings": settings}


def do_run(args) -> None:
    state = do_setup(args)
    python, settings = state["python"], state["settings"]

    if season_row_count(settings["db"], settings["season"]) == 0:
        sys.exit("Still no data after the backfill - check the messages above.")

    print("\nProjecting team totals ...\n")
    cmd = [python, "-m", "hrproj.cli", "project", "--format", "html,csv"]
    if args.sims:
        cmd += ["--sims", args.sims]
    run(cmd)

    # The data is already current after the team run, so skip the second fetch.
    print("\nProjecting individual hitters ...\n")
    hitters = [
        python, "-m", "hrproj.cli", "leaders", "--no-refresh",
        "--format", "html,csv", "--top", "40",
    ]
    if args.sims:
        hitters += ["--sims", args.sims]
    run(hitters)

    report = newest_report(PROJECT_DIR / "out")
    if report and not args.no_open:
        print(f"\nOpening {report}")
        open_file(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--reinstall", action="store_true", help="Reinstall the packages")
    common.add_argument("--sims", help="Monte Carlo iterations (default 10000)")
    common.add_argument("--no-open", action="store_true", help="Do not open the report")

    sub.add_parser("setup", parents=[common], help="Install and backfill, without projecting")
    sub.add_parser("run", parents=[common], help="Set up if needed, update data, project")

    args = parser.parse_args()
    if args.command == "setup":
        do_setup(args)
        print("\nSetup complete. Run run.bat (or python tools/bootstrap.py run) to project.")
    else:
        do_run(args)


if __name__ == "__main__":
    main()
