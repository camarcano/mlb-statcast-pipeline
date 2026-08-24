@echo off
REM Update the Statcast data and produce the projection. Sets itself up on first run.
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 tools\bootstrap.py run
) else (
    python tools\bootstrap.py run
)

if errorlevel 1 (
    echo.
    echo Something went wrong. If this is the first run, try setup.bat first.
)
echo.
pause
