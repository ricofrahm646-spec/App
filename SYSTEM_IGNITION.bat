@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo [JARVIS] Creating venv...
if not exist ".venv\Scripts\activate.bat" (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo [JARVIS] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [JARVIS] Installing Playwright Chromium...
python -m playwright install chromium
if errorlevel 1 exit /b 1

echo [JARVIS] Ignition — starting controller...
python jarvis.py --mode all
endlocal
