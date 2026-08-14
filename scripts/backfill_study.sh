#!/usr/bin/env bash
# Backfill regular-season Statcast data for the pitch-homogeneity study.
# Seasons run most-recent-first so analysis code can be validated on complete
# recent data while earlier seasons are still downloading. Resumable: days
# already recorded as successful in fetch_log are skipped.
set -u

LOG_DIR="$(dirname "$0")/../logs"
mkdir -p "$LOG_DIR"

# Regular-season windows (inclusive), widened a few days on each end.
run_season() {
    local year="$1" start="$2" end="$3"
    echo "=== season ${year}: ${start} .. ${end} (started $(date -u +%FT%TZ)) ==="
    statcast backfill --start-date "$start" --end-date "$end" --game-types R
    echo "=== season ${year} finished with exit ${?} at $(date -u +%FT%TZ) ==="
}

run_season 2025 2025-03-18 2025-09-29
run_season 2024 2024-03-20 2024-09-30
run_season 2023 2023-03-30 2023-10-02
run_season 2022 2022-04-07 2022-10-05
run_season 2021 2021-04-01 2021-10-04

echo "ALL SEASONS COMPLETE $(date -u +%FT%TZ)"
