#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$INSTALL_DIR/venv"
LOG_FILE="$INSTALL_DIR/logs/cron.log"

mkdir -p "$INSTALL_DIR/logs"

CRON_CMD="33 3 * * * cd $INSTALL_DIR && $VENV_DIR/bin/statcast update --days-back 2 >> $LOG_FILE 2>&1"

EXISTING=$(crontab -l 2>/dev/null | grep -v "statcast" || true)

if [ -z "$EXISTING" ]; then
    echo "$CRON_CMD" | crontab -
else
    echo "$EXISTING"$'\n'"$CRON_CMD" | crontab -
fi

echo "Cron job configured: daily at 3:33 AM UTC"
echo "Verify with: crontab -l"
