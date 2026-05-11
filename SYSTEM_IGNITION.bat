@echo off
setlocal EnableDelayedExpansion
title JARVIS V300 SYSTEM IGNITION

cd /d "%~dp0"
echo ==========================================================
echo   J.A.R.V.I.S V300 OMNIPOTENCE - SYSTEM IGNITION
echo ==========================================================

if not exist ".venv" (
    echo [1/6] Creating virtual environment...
    python -m venv .venv
)

echo [2/6] Activating virtual environment...
call ".venv\Scripts\activate.bat"

echo [3/6] Upgrading pip tooling...
python -m pip install --upgrade pip setuptools wheel

echo [4/6] Installing Python dependencies...
pip install -r requirements.txt

echo [5/6] Installing Playwright Chromium runtime...
python -m playwright install chromium

if not exist "apps" (
    echo [6/6] Creating /apps workspace...
    mkdir apps
) else (
    echo [6/6] /apps workspace already present.
)

echo.
echo Launching JARVIS Core and War Room dashboard...
start "JARVIS CORE" cmd /k "call .venv\Scripts\activate.bat && python jarvis.py --symbol EURUSD"
start "JARVIS WAR ROOM" cmd /k "call .venv\Scripts\activate.bat && streamlit run ui.py"

echo Boot sequence complete. Sir, the machine is running.
endlocal
