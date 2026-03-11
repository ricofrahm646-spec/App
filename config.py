"""
Configuration for the Binance EUR momentum trading bot.
All tunables are defined here to keep trading_bot.py free of magic numbers.
"""

# ---------------------------------------------------------------------------
# Exchange
# ---------------------------------------------------------------------------
EXCHANGE_ID = "binance"
QUOTE_CURRENCY = "EUR"

# API credentials – set via environment variables, never hard-code secrets.
# export BINANCE_API_KEY="..."
# export BINANCE_API_SECRET="..."

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
OHLCV_TIMEFRAME = "5m"        # candle timeframe used for all indicators
OHLCV_LIMIT = 100             # number of candles fetched per symbol
REQUEST_DELAY_SECONDS = 0.2   # politeness delay between per-symbol requests

# ---------------------------------------------------------------------------
# Indicator periods
# ---------------------------------------------------------------------------
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2.0
VOLUME_BASELINE_CANDLES = 5   # rolling window for volume baseline

# ---------------------------------------------------------------------------
# Scoring model weights  (must sum to 1.0)
# ---------------------------------------------------------------------------
SCORE_WEIGHT_PRICE_MOMENTUM = 0.40
SCORE_WEIGHT_VOLUME_SPIKE   = 0.30
SCORE_WEIGHT_RSI            = 0.15
SCORE_WEIGHT_MACD           = 0.10
SCORE_WEIGHT_BB             = 0.05

assert abs(
    SCORE_WEIGHT_PRICE_MOMENTUM
    + SCORE_WEIGHT_VOLUME_SPIKE
    + SCORE_WEIGHT_RSI
    + SCORE_WEIGHT_MACD
    + SCORE_WEIGHT_BB
    - 1.0
) < 1e-9, "Scoring weights must sum to exactly 1.0"

# Normalisation caps used when mapping a raw value → [0, 1]
SCORE_PRICE_CAP_PCT   = 5.0    # 5 % price change → full score
SCORE_VOLUME_CAP_PCT  = 300.0  # 300 % volume change → full score
SCORE_RSI_LOW         = 50.0   # RSI below this → partial score
SCORE_RSI_HIGH        = 70.0   # RSI above this → full score

# Minimum score to include a coin in the high-conviction signal log
SIGNAL_SCORE_THRESHOLD = 80

# ---------------------------------------------------------------------------
# Pump detection
# ---------------------------------------------------------------------------
PUMP_MIN_PRICE_CHANGE_PCT  = 2.0    # % price gain in last candle
PUMP_MIN_VOLUME_SPIKE_PCT  = 150.0  # % above rolling-average volume

# ---------------------------------------------------------------------------
# Ranking & auto-trading
# ---------------------------------------------------------------------------
TOP_N_COINS = 3               # number of top-ranked coins to trade

# Risk management
TRADE_BALANCE_MIN_PCT = 0.30  # minimum fraction of EUR balance per trade
TRADE_BALANCE_MAX_PCT = 0.50  # maximum fraction of EUR balance per trade
STOP_LOSS_PCT         = 0.02  # 2 % stop-loss below entry
TAKE_PROFIT_PCT       = 0.07  # 7 % take-profit above entry (mid of 5–10 %)

# ---------------------------------------------------------------------------
# Retry settings (for transient API errors)
# ---------------------------------------------------------------------------
RETRY_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2.0

# ---------------------------------------------------------------------------
# Scan loop
# ---------------------------------------------------------------------------
SCAN_INTERVAL_SECONDS = 300   # 5 minutes between full scans

# ---------------------------------------------------------------------------
# Logging / output paths
# ---------------------------------------------------------------------------
SIGNALS_CSV_PATH = "signals.csv"
TRADES_CSV_PATH  = "trades.csv"
