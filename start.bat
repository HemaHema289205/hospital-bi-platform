@echo off
REM =====================================================================
REM  HospitalFlow AI - start both servers (Windows)
REM  Opens the backend in its own window, then runs the frontend here.
REM =====================================================================
cd /d "%~dp0"

echo Starting backend  -^> http://127.0.0.1:8000/docs
start "HospitalFlow API" cmd /k python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

timeout /t 4 /nobreak >nul

echo Starting frontend -^> http://127.0.0.1:5173
cd frontend
call npm run dev
