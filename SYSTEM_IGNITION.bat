@echo off
title J.A.R.V.I.S. V300 - SYSTEM IGNITION
color 0B
echo.
echo  ===================================================
echo   J.A.R.V.I.S. V300 - OMNIPOTENCE PROTOCOL
echo   SYSTEM IGNITION SEQUENCE
echo  ===================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)
echo [OK] Python detected

:: Create virtual environment
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
)
echo [OK] Virtual environment ready

:: Activate venv
call venv\Scripts\activate.bat
echo [OK] Environment activated

:: Install dependencies
echo [*] Installing core dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo [OK] Core packages installed

:: Install MetaTrader5 (Windows only)
echo [*] Installing MetaTrader5 API...
pip install MetaTrader5 2>nul
if errorlevel 1 (
    echo [WARN] MetaTrader5 install failed - will run in simulation mode
) else (
    echo [OK] MetaTrader5 installed
)

:: Install Playwright browsers
echo [*] Setting up Playwright...
python -m playwright install chromium 2>nul
if errorlevel 1 (
    echo [WARN] Playwright setup failed - news scraping may be limited
) else (
    echo [OK] Playwright configured
)

:: Create directories
if not exist "apps" mkdir apps
if not exist "logs" mkdir logs
if not exist "data" mkdir data
echo [OK] Directories created

echo.
echo  ===================================================
echo   ALL SYSTEMS GO
echo  ===================================================
echo.
echo  [1] Launch J.A.R.V.I.S. (Full System)
echo  [2] Launch Dashboard Only
echo  [3] Launch J.A.R.V.I.S. (No Voice)
echo  [4] Exit
echo.
set /p choice="Select mode: "

if "%choice%"=="1" (
    echo [*] Starting J.A.R.V.I.S. V300...
    python jarvis.py
) else if "%choice%"=="2" (
    echo [*] Starting War Room Dashboard...
    streamlit run core/ui.py --server.port 8501 --theme.base dark
) else if "%choice%"=="3" (
    echo [*] Starting J.A.R.V.I.S. (silent mode)...
    python jarvis.py --no-voice
) else (
    echo Exiting.
)

pause
