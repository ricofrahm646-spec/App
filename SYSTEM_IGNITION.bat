@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo [JARVIS] Bootstrapping Python environment...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [JARVIS] Installing Playwright Chromium runtime...
python -m playwright install chromium

if not exist "apps" mkdir "apps"

echo [JARVIS] Launching War Room dashboard...
start "JARVIS War Room" cmd /k "python -m streamlit run ui.py"

echo [JARVIS] Launching control core...
python jarvis.py --workspace . --symbol EURUSD --mode paper

endlocal
