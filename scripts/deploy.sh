#!/bin/bash
set -e

INSTALL_DIR="${INSTALL_DIR:-/opt/mlb-statcast-pipeline}"
VENV_DIR="$INSTALL_DIR/venv"
REPO_NAME="mlb-statcast-pipeline"

echo "=== MLB Statcast Pipeline Deployment ==="

if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "ERROR: $INSTALL_DIR/.env not found."
    echo "Create it from .env.example with your GH_PAT and GH_USERNAME."
    exit 1
fi

source "$INSTALL_DIR/.env"

if [ -z "$GH_PAT" ] || [ -z "$GH_USERNAME" ]; then
    echo "ERROR: GH_PAT and GH_USERNAME must be set in .env"
    exit 1
fi

REPO_URL="https://${GH_PAT}@github.com/${GH_USERNAME}/${REPO_NAME}.git"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

if [ ! -f "$INSTALL_DIR/data/savant.db" ]; then
    echo "Initializing database..."
    statcast init
    echo "Running initial backfill (this will take a while)..."
    statcast backfill
else
    echo "Database already exists. Running update..."
    statcast update --days-back 3
fi

echo "Setting up cron job..."
bash "$INSTALL_DIR/scripts/setup_cron.sh"

echo ""
echo "=== Deployment complete ==="
echo "CLI: $VENV_DIR/bin/statcast"
echo "DB:  $INSTALL_DIR/data/savant.db"
echo "Log: $INSTALL_DIR/logs/statcast.log"
