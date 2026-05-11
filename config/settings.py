"""
J.A.R.V.I.S. V300 - Global Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "apps"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

APPS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# --- MT5 Configuration ---
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")

# --- Trading Parameters ---
TRADING = {
    "symbol": os.getenv("TRADE_SYMBOL", "EURUSD"),
    "timeframe_scalp": "M1",
    "timeframe_confirm": "M5",
    "max_risk_pct": 2.0,
    "max_daily_loss_pct": 6.0,
    "trail_stop_atr_mult": 1.5,
    "confluence_threshold": 0.90,
    "lot_size_start": 0.01,
    "spread_limit_points": 15,
    "slippage": 5,
    "news_blackout_minutes": 30,
}

# --- SMC Parameters ---
SMC = {
    "ob_lookback": 50,
    "fvg_min_gap_pips": 3.0,
    "liquidity_sweep_threshold_pips": 2.0,
    "bos_lookback": 20,
    "choch_lookback": 20,
}

# --- Dashboard ---
DASHBOARD = {
    "refresh_interval_sec": 2,
    "max_log_lines": 500,
    "chart_candles": 200,
}

# --- Voice ---
VOICE = {
    "wake_word": "jarvis",
    "speech_rate": 175,
    "volume": 0.9,
    "voice_id": 0,
}

# --- OpenAI (for code generation) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# --- Ghost Engine ---
GHOST = {
    "headless": True,
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "news_sources": [
        "https://www.forexfactory.com/calendar",
        "https://www.investing.com/economic-calendar/",
    ],
}
