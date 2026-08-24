@echo off
REM First-time setup: virtual environment, packages, and the season download.
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 tools\bootstrap.py setup
) else (
    python tools\bootstrap.py setup
)

if errorlevel 1 (
    echo.
    echo Setup failed. If Python was not found, install it from
    echo https://www.python.org/downloads/ and tick "Add python.exe to PATH".
)
echo.
pause
