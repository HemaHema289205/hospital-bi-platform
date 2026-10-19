#!/usr/bin/env bash
# =====================================================================
#  HospitalFlow AI - start both servers (macOS / Linux)
#  Run:  bash start.sh      Stop: Ctrl+C
# =====================================================================
cd "$(dirname "$0")"

echo "Starting backend  -> http://127.0.0.1:8000/docs"
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# give the API a moment to come up before the browser opens
sleep 3

echo "Starting frontend -> http://127.0.0.1:5173"
cd frontend && npm run dev
kill $BACKEND_PID 2>/dev/null
