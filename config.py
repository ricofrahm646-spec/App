"""
Configuration for the Hardcore Growth Mode crypto trading bot.
All settings are loaded from environment variables (see .env.example).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Exchange
EXCHANGE_ID: str = os.getenv("EXCHANGE_ID", "kraken")
API_KEY: str = os.getenv("API_KEY", "")
API_SECRET: str = os.getenv("API_SECRET", "")

# Quote currency (always EUR for EUR-pair trading)
QUOTE_CURRENCY: str = os.getenv("QUOTE_CURRENCY", "EUR")

# Scanning
SCAN_INTERVAL_MIN: int = int(os.getenv("SCAN_INTERVAL_MIN", "20"))  # seconds
SCAN_INTERVAL_MAX: int = int(os.getenv("SCAN_INTERVAL_MAX", "30"))  # seconds

# Scoring thresholds
RSI_THRESHOLD: float = float(os.getenv("RSI_THRESHOLD", "40"))
MACD_POSITIVE: bool = os.getenv("MACD_POSITIVE", "true").lower() == "true"
VOLUME_SPIKE_RATIO: float = float(os.getenv("VOLUME_SPIKE_RATIO", "1.5"))  # 150%
PRICE_INCREASE_THRESHOLD: float = float(
    os.getenv("PRICE_INCREASE_THRESHOLD", "0.02")
)  # 2%
MIN_SCORE: int = int(os.getenv("MIN_SCORE", "80"))
MAX_TOP_COINS: int = int(os.getenv("MAX_TOP_COINS", "3"))

# Trade sizing
TRADE_AMOUNT_PERCENT_MIN: float = float(
    os.getenv("TRADE_AMOUNT_PERCENT_MIN", "0.30")
)  # 30%
TRADE_AMOUNT_PERCENT_MAX: float = float(
    os.getenv("TRADE_AMOUNT_PERCENT_MAX", "0.50")
)  # 50%

# Risk management
STOP_LOSS_PERCENT: float = float(os.getenv("STOP_LOSS_PERCENT", "0.025"))   # 2.5%
TAKE_PROFIT_PERCENT: float = float(os.getenv("TAKE_PROFIT_PERCENT", "0.075"))  # 7.5%

# Trade retry
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))  # seconds between retries

# Telegram alerts
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# Logging / persistence
DATA_DIR: str = os.getenv("DATA_DIR", "data")
HISTORY_FILE: str = os.path.join(DATA_DIR, "history.csv")
STATE_FILE: str = os.path.join(DATA_DIR, "state.json")
LOG_FILE: str = os.path.join(DATA_DIR, "bot.log")

# OHLCV candle timeframe and lookback for indicator calculation
CANDLE_TIMEFRAME: str = os.getenv("CANDLE_TIMEFRAME", "1m")
CANDLE_LIMIT: int = int(os.getenv("CANDLE_LIMIT", "100"))

# ── Runtime validation ────────────────────────────────────────────────
if STOP_LOSS_PERCENT >= TAKE_PROFIT_PERCENT:
    raise ValueError(
        f"STOP_LOSS_PERCENT ({STOP_LOSS_PERCENT}) must be less than "
        f"TAKE_PROFIT_PERCENT ({TAKE_PROFIT_PERCENT})."
    )
if not (0 < TRADE_AMOUNT_PERCENT_MIN <= TRADE_AMOUNT_PERCENT_MAX <= 1):
    raise ValueError(
        "TRADE_AMOUNT_PERCENT_MIN and _MAX must satisfy 0 < min ≤ max ≤ 1."
    )
