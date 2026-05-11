@echo off
REM ===========================================================================
REM  J.A.R.V.I.S. V300 OMNIPOTENCE  -  SYSTEM IGNITION
REM ---------------------------------------------------------------------------
REM  This batch file:
REM    1. creates a local virtual environment (.venv)
REM    2. installs every dependency from requirements.txt
REM    3. installs the Playwright browser binaries (Chromium stealth)
REM    4. launches the Streamlit War-Room dashboard in a new window
REM    5. launches the master brain (jarvis.py) in the foreground
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  ============================================================
echo            J.A.R.V.I.S. V300 OMNIPOTENCE - IGNITION
echo  ============================================================
echo.

REM --- locate Python ---------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [FATAL] Python is not on PATH. Install Python 3.10+ and retry.
    pause
    exit /b 1
)

REM --- virtual environment ---------------------------------------------------
if not exist ".venv" (
    echo [BOOT] creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [FATAL] failed to create venv
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate.bat

REM --- pip / wheel up to date -----------------------------------------------
echo [BOOT] upgrading pip ...
python -m pip install --upgrade pip wheel setuptools

REM --- install dependencies --------------------------------------------------
echo [BOOT] installing requirements.txt ...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [WARN] some requirements failed to install - continuing best effort
)

REM --- Playwright browsers ---------------------------------------------------
echo [BOOT] downloading Playwright browsers (Chromium) ...
python -m playwright install chromium

REM --- ensure runtime directories exist --------------------------------------
if not exist "logs" mkdir logs
if not exist "apps" mkdir apps
if not exist "data\state" mkdir data\state
if not exist "data\research" mkdir data\research
if not exist "data\screenshots" mkdir data\screenshots

REM --- launch dashboard in a new window --------------------------------------
echo [BOOT] launching War-Room dashboard ...
start "JARVIS War-Room" cmd /k "call .venv\Scripts\activate.bat && streamlit run ui.py --server.headless false"

REM small delay so the dashboard binds first
timeout /t 3 /nobreak >nul

REM --- launch master brain ---------------------------------------------------
echo [BOOT] launching master brain ...
python jarvis.py %*

endlocal
