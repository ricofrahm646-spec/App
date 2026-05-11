@echo off
setlocal

cd /d %~dp0
echo [JARVIS] Updating Python tooling...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [JARVIS] Installing core dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [JARVIS] Installing Playwright browser runtime...
python -m playwright install chromium
if errorlevel 1 goto :fail

if not exist runtime mkdir runtime
if not exist apps mkdir apps

echo [JARVIS] Launching master brain...
start "JARVIS Core" cmd /k python jarvis.py --loop

echo [JARVIS] Launching war room dashboard...
start "JARVIS War Room" cmd /k streamlit run ui.py

echo [JARVIS] System ignition complete.
exit /b 0

:fail
echo [JARVIS] Ignition failed with error code %errorlevel%.
exit /b %errorlevel%
