@echo off
setlocal ENABLEDELAYEDEXPANSION
title J.A.R.V.I.S. V300 SYSTEM IGNITION

echo [JARVIS] Initializing V300 stack for you, Sir.
where python >nul 2>nul
if errorlevel 1 (
    echo [JARVIS] Python is not available on PATH.
    exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

python -m playwright install chromium
if errorlevel 1 exit /b 1

if not exist apps mkdir apps

set JARVIS_LIVE_TRADING=0
set JARVIS_OS_CONTROL=0

echo [JARVIS] Running initial code audit.
python ghost_security.py

echo [JARVIS] Launching Universal Creator shell.
streamlit run ui/main_shell.py

endlocal
