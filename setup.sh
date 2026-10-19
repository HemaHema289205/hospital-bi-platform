#!/usr/bin/env bash
# =====================================================================
#  HospitalFlow AI - one-time setup (macOS / Linux)
#  Run:  bash setup.sh
# =====================================================================
set -e
cd "$(dirname "$0")"

echo
echo "=============================================="
echo "  HospitalFlow AI - setup"
echo "=============================================="

echo
echo "[1/4] Installing Python packages..."
python3 -m pip install -r requirements.txt

echo
echo "[2/4] Creating .env (if it does not exist)..."
[ -f .env ] || cp .env.example .env

echo
echo "[3/4] Building the database and training the models..."
python3 scripts/run_pipeline.py

echo
echo "[4/4] Installing frontend packages..."
cd frontend && npm install && cd ..

echo
echo "=============================================="
echo "  Setup complete."
echo "  Now run:  bash start.sh"
echo "=============================================="

