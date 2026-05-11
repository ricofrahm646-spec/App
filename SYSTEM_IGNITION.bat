@echo off
setlocal EnableExtensions

echo [JARVIS] Initializing V300 War Room, Sir.

if not exist ".venv" (
  echo [JARVIS] Creating Python virtual environment...
  py -3 -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo [JARVIS] Upgrading pip...
python -m pip install --upgrade pip

echo [JARVIS] Installing libraries...
python -m pip install -r requirements.txt

echo [JARVIS] Installing Playwright Chromium runtime...
python -m playwright install chromium

if not exist "logs" mkdir logs
if not exist "apps" mkdir apps
if not exist "research_cache" mkdir research_cache

set JARVIS_PAPER_TRADING=1
set JARVIS_CONTROL_DRY_RUN=1

echo [JARVIS] Safety gates active: PAPER trading and DRY-RUN OS control.
echo [JARVIS] Starting War Room dashboard...
start "JARVIS V300 War Room" python -m streamlit run ui.py

echo [JARVIS] Starting Master Brain console...
python jarvis.py --interactive

endlocal
