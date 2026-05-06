#!/bin/bash
set -e

# Usage: Run this AFTER cloning the repo manually.
#   bash scripts/deploy.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$INSTALL_DIR/venv"

echo "=== MLB Statcast Pipeline Setup ==="
echo "Install dir: $INSTALL_DIR"
echo ""

# 1. Verify .env exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "ERROR: .env not found in $INSTALL_DIR"
    echo "Create one from .env.example before running this script."
    echo ""
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# 2. Verify Python 3.10+
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# 3. Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# 4. Install dependencies
echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$INSTALL_DIR/requirements.txt" --quiet
pip install -e "$INSTALL_DIR" --quiet

# 5. Initialize database
if [ ! -f "$INSTALL_DIR/data/savant.db" ]; then
    echo "Initializing database..."
    statcast init
    echo ""
    echo "Database created. Run the backfill to load historical data:"
    echo "  source $VENV_DIR/bin/activate"
    echo "  statcast backfill"
else
    echo "Database already exists. Running update..."
    statcast update --days-back 3
fi

# 6. Set up cron job
echo ""
bash "$INSTALL_DIR/scripts/setup_cron.sh"

echo ""
echo "=== Setup complete ==="
echo "CLI:     $VENV_DIR/bin/statcast"
echo "DB:      $INSTALL_DIR/data/savant.db"
echo "Logs:    $INSTALL_DIR/logs/"
echo ""
echo "Quick commands:"
echo "  statcast status    - View database stats"
echo "  statcast backfill  - Load 2025-present data"
echo "  statcast update    - Fetch latest data"
echo "  statcast audit     - Check for missing data"
