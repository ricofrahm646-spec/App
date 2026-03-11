"""
Configuration parameters for the Binance EUR Trading Bot.
"""

# ── Scanning ───────────────────────────────────────────────────────────────────
SCAN_INTERVAL_SECONDS: int = 300        # 5 minutes between scans (1–5 min range)
OHLCV_LIMIT: int = 100                  # candles to fetch per pair
TIMEFRAME: str = "5m"                   # candle timeframe used for all calculations

# ── Momentum-pump thresholds ───────────────────────────────────────────────────
PRICE_INCREASE_THRESHOLD: float = 2.0   # % price rise required over last candle
VOLUME_SPIKE_THRESHOLD: float = 150.0   # % volume increase vs. rolling average

# ── Scoring ────────────────────────────────────────────────────────────────────
SCORE_THRESHOLD: int = 80               # minimum score to log a trade signal

# Score component weights (must sum to 100)
SCORE_WEIGHT_PRICE: int = 40            # price-momentum score weight
SCORE_WEIGHT_VOLUME: int = 30           # volume-spike score weight
SCORE_WEIGHT_RSI: int = 15              # RSI score weight
SCORE_WEIGHT_MACD: int = 10             # MACD score weight
SCORE_WEIGHT_BB: int = 5                # Bollinger Bands score weight

# ── Technical indicator parameters ────────────────────────────────────────────
RSI_PERIOD: int = 14
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9
BB_PERIOD: int = 20
BB_STD_DEV: float = 2.0

# ── Volume-change lookback ─────────────────────────────────────────────────────
VOLUME_LOOKBACK: int = 5                # candles to average for "recent" volume
VOLUME_BASELINE: int = 5               # candles to average for baseline volume

# ── Output files ──────────────────────────────────────────────────────────────
CSV_FILE: str = "trades_log.csv"
LOG_FILE: str = "trading_bot.log"

# ── Exchange ───────────────────────────────────────────────────────────────────
EXCHANGE_ID: str = "binance"
QUOTE_CURRENCY: str = "EUR"
REQUEST_DELAY_SECONDS: float = 0.2     # polite delay between API calls
