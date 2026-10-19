@echo off
REM =====================================================================
REM  HospitalFlow AI - one-time setup (Windows)
REM  Double-click this file, or run:  setup.bat
REM =====================================================================
cd /d "%~dp0"

echo.
echo ==============================================
echo   HospitalFlow AI - setup
echo ==============================================

echo.
echo [1/4] Installing Python packages...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo [2/4] Creating .env (if it does not exist)...
if not exist .env copy .env.example .env >nul

echo.
echo [3/4] Building the database and training the models...
python scripts\run_pipeline.py
if errorlevel 1 goto :error

echo.
echo [4/4] Installing frontend packages...
cd frontend
call npm install
if errorlevel 1 goto :error
cd ..

echo.
echo ==============================================
echo   Setup complete.
echo   Now run:  start.bat
echo ==============================================
pause
exit /b 0

:error
echo.
echo Setup failed. Read the error message above.
pause
exit /b 1
