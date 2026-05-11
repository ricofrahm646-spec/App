@echo off
title J.A.R.V.I.S. V300 — SYSTEM IGNITION
color 0B
cls

echo.
echo  ========================================================
echo   J.A.R.V.I.S. V300 OMNIPOTENCE — SYSTEM IGNITION
echo   Sir, initializing all systems...
echo  ========================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

echo  [1/5] Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  [WARN] Some packages may have failed. Continuing...
)

echo.
echo  [2/5] Installing Playwright browsers...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo  [WARN] Playwright browser install failed. Ghost mode may be limited.
)

echo.
echo  [3/5] Creating directory structure...
if not exist "apps" mkdir apps
if not exist "logs" mkdir logs
if not exist "config" mkdir config

echo.
echo  [4/5] Creating .env template (if not exists)...
if not exist ".env" (
    echo # J.A.R.V.I.S. V300 Configuration> .env
    echo MT5_LOGIN=0>> .env
    echo MT5_PASSWORD=>> .env
    echo MT5_SERVER=>> .env
    echo MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe>> .env
    echo OPENAI_API_KEY=>> .env
    echo OPENAI_MODEL=gpt-4o>> .env
    echo TRADE_SYMBOL=EURUSD>> .env
    echo  [INFO] .env file created — edit it with your credentials.
) else (
    echo  [INFO] .env already exists — skipping.
)

echo.
echo  [5/5] Running initial security scan...
python -c "from ghost_security import SecurityScanner; s = SecurityScanner(); print(f'Scan: {s.get_summary()}')" 2>nul
if %errorlevel% neq 0 (
    echo  [WARN] Security scan skipped.
)

echo.
echo  ========================================================
echo   IGNITION COMPLETE — All systems ready
echo  ========================================================
echo.
echo  Launch options:
echo    1. Dashboard:   streamlit run ui.py
echo    2. Jarvis CLI:  python jarvis.py
echo    3. Auto Mode:   python jarvis.py --auto
echo    4. Voice Mode:  python jarvis.py --voice
echo    5. Trader Only: python trader_ultimate.py
echo.

set /p choice="  Select mode (1-5) or press Enter for Dashboard: "

if "%choice%"=="1" goto DASHBOARD
if "%choice%"=="2" goto CLI
if "%choice%"=="3" goto AUTO
if "%choice%"=="4" goto VOICE
if "%choice%"=="5" goto TRADER

:DASHBOARD
echo.
echo  Launching War Room Dashboard...
streamlit run ui.py --server.port 8501 --theme.base dark
goto END

:CLI
echo.
echo  Launching J.A.R.V.I.S. Interactive Mode...
python jarvis.py
goto END

:AUTO
echo.
echo  Launching J.A.R.V.I.S. Full Autonomous Mode...
python jarvis.py --auto
goto END

:VOICE
echo.
echo  Launching J.A.R.V.I.S. Voice Control Mode...
python jarvis.py --voice
goto END

:TRADER
echo.
echo  Launching Trading Engine...
python trader_ultimate.py
goto END

:END
pause
