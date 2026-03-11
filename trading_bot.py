"""
Binance EUR momentum trading bot.

Pipeline
--------
1. Fetch all EUR trading pairs from Binance.
2. For every pair, download the last N 5-minute candles.
3. Compute RSI, MACD, Bollinger Bands, and volume-change indicators.
4. Score momentum strength (0-100) and detect pump signals.
5. Rank coins by score; select the top-N candidates for live trading.
6. For each top-N coin:
   a. Retrieve current EUR balance.
   b. Allocate 30-50 % of balance for the trade.
   c. Place a market buy order.
   d. Place stop-loss and take-profit limit sell orders.
   e. Log the trade to CSV (timestamp, coin, entry, exit targets, P/L, score).
7. Repeat every SCAN_INTERVAL_SECONDS.

All API calls use automatic retry logic to handle transient errors.
High-conviction signals (score ≥ SIGNAL_SCORE_THRESHOLD) are also written
to a separate signals CSV.
"""

from __future__ import annotations

import csv
import logging
import math
import os
import signal as _signal
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

import ccxt
import numpy as np
import pandas as pd

import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

SIGNALS_FIELDNAMES: List[str] = [
    "timestamp",
    "symbol",
    "price",
    "price_change_pct",
    "volume_change_pct",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_upper",
    "bb_middle",
    "bb_lower",
    "score",
    "is_pump",
]

TRADES_FIELDNAMES: List[str] = [
    "timestamp",
    "symbol",
    "score",
    "entry_price",
    "stop_loss_price",
    "take_profit_price",
    "amount_eur",
    "amount_coin",
    "exit_price",
    "pnl_eur",
    "status",
]


def _ensure_csv(path: str, fieldnames: List[str]) -> None:
    """Create the CSV file with a header row if it does not already exist."""
    if not os.path.exists(path):
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()


def log_signal(signal: Dict[str, Any], path: str = config.SIGNALS_CSV_PATH) -> None:
    """Append a scored signal row to the signals CSV."""
    _ensure_csv(path, SIGNALS_FIELDNAMES)
    row = {k: signal.get(k, "") for k in SIGNALS_FIELDNAMES}
    with open(path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SIGNALS_FIELDNAMES)
        writer.writerow(row)


def log_trade(trade: Dict[str, Any], path: str = config.TRADES_CSV_PATH) -> None:
    """Append an executed (or attempted) trade row to the trades CSV."""
    _ensure_csv(path, TRADES_FIELDNAMES)
    row = {k: trade.get(k, "") for k in TRADES_FIELDNAMES}
    with open(path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TRADES_FIELDNAMES)
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry_on_error(
    max_attempts: int = config.RETRY_MAX_ATTEMPTS,
    delay_seconds: float = config.RETRY_DELAY_SECONDS,
    exceptions: Tuple[type, ...] = (ccxt.NetworkError, ccxt.ExchangeError),
) -> Callable:
    """Decorator – re-call the wrapped function on *exceptions* up to
    *max_attempts* times, sleeping *delay_seconds* between tries."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    logger.warning(
                        "API error on attempt %d/%d for %s: %s",
                        attempt,
                        max_attempts,
                        fn.__name__,
                        exc,
                    )
                    if attempt < max_attempts:
                        time.sleep(delay_seconds)
                    else:
                        raise  # re-raise after all retries exhausted

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Exchange initialisation
# ---------------------------------------------------------------------------

def create_exchange() -> ccxt.Exchange:
    """Create and return a configured ccxt Binance exchange instance.

    API credentials are read from environment variables so that secrets are
    never stored in source code or configuration files.
    """
    exchange = ccxt.binance(
        {
            "apiKey": os.environ.get("BINANCE_API_KEY", ""),
            "secret": os.environ.get("BINANCE_API_SECRET", ""),
            "enableRateLimit": True,
        }
    )
    return exchange


# ---------------------------------------------------------------------------
# Market data helpers
# ---------------------------------------------------------------------------

@retry_on_error()
def fetch_eur_pairs(exchange: ccxt.Exchange) -> List[str]:
    """Return all active spot symbols quoted in EUR."""
    markets = exchange.load_markets()
    return [
        sym
        for sym, mkt in markets.items()
        if mkt.get("quote") == config.QUOTE_CURRENCY
        and mkt.get("active", True)
        and mkt.get("spot", True)
    ]


@retry_on_error()
def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str) -> Optional[pd.DataFrame]:
    """Fetch OHLCV candles and return a DataFrame with columns
    [open, high, low, close, volume].  Returns *None* on data issues."""
    raw = exchange.fetch_ohlcv(
        symbol,
        timeframe=config.OHLCV_TIMEFRAME,
        limit=config.OHLCV_LIMIT,
    )
    if not raw or len(raw) < config.BB_PERIOD:
        return None
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def compute_rsi(closes: pd.Series, period: int = config.RSI_PERIOD) -> float:
    """Wilder RSI for the most-recent candle.  Returns NaN on insufficient data."""
    if len(closes) < period + 1:
        return float("nan")
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 4)


def compute_macd(
    closes: pd.Series,
    fast: int = config.MACD_FAST,
    slow: int = config.MACD_SLOW,
    signal: int = config.MACD_SIGNAL,
) -> Tuple[float, float, float]:
    """Return (macd_line, signal_line, histogram) for the most-recent candle."""
    if len(closes) < slow + signal:
        nan = float("nan")
        return nan, nan, nan
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    sig_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - sig_line
    return (
        round(macd_line.iloc[-1], 8),
        round(sig_line.iloc[-1], 8),
        round(hist.iloc[-1], 8),
    )


def compute_bollinger_bands(
    closes: pd.Series,
    period: int = config.BB_PERIOD,
    num_std: float = config.BB_STD,
) -> Tuple[float, float, float]:
    """Return (upper, middle, lower) Bollinger Bands for the most-recent candle."""
    if len(closes) < period:
        nan = float("nan")
        return nan, nan, nan
    rolling = closes.rolling(period)
    middle = rolling.mean().iloc[-1]
    std = rolling.std(ddof=0).iloc[-1]
    upper = middle + num_std * std
    lower = middle - num_std * std
    return round(upper, 8), round(middle, 8), round(lower, 8)


def compute_volume_change(
    volumes: pd.Series,
    baseline_candles: int = config.VOLUME_BASELINE_CANDLES,
) -> float:
    """Percentage change of the last candle's volume vs the rolling baseline
    of the *baseline_candles* candles before it."""
    if len(volumes) < baseline_candles + 1:
        return float("nan")
    baseline = volumes.iloc[-(baseline_candles + 1) : -1].mean()
    if baseline == 0:
        return float("nan")
    current = volumes.iloc[-1]
    return round((current - baseline) / baseline * 100.0, 4)


def compute_price_change(closes: pd.Series) -> float:
    """Percentage price change between the second-to-last and last close."""
    if len(closes) < 2:
        return float("nan")
    prev = closes.iloc[-2]
    if prev == 0:
        return float("nan")
    return round((closes.iloc[-1] - prev) / prev * 100.0, 4)


# ---------------------------------------------------------------------------
# Scoring & pump detection
# ---------------------------------------------------------------------------

def score_coin(
    price_change_pct: float,
    volume_change_pct: float,
    rsi: float,
    macd_line: float,
    macd_signal_val: float,
    macd_hist: float,
    price: float,
    bb_upper: float,
    bb_middle: float,
) -> float:
    """Composite momentum score in [0, 100].

    Returns 0.0 when any required value is NaN.
    """
    for v in (price_change_pct, volume_change_pct, rsi, macd_line, macd_signal_val, macd_hist, price, bb_upper, bb_middle):
        if math.isnan(v):
            return 0.0

    # --- price momentum component (0-1) ---
    price_score = min(max(price_change_pct, 0.0), config.SCORE_PRICE_CAP_PCT) / config.SCORE_PRICE_CAP_PCT

    # --- volume spike component (0-1) ---
    volume_score = min(max(volume_change_pct, 0.0), config.SCORE_VOLUME_CAP_PCT) / config.SCORE_VOLUME_CAP_PCT

    # --- RSI component (0-1); optimal range 50-70 ---
    if rsi < config.SCORE_RSI_LOW:
        rsi_score = rsi / config.SCORE_RSI_LOW * 0.5
    elif rsi <= config.SCORE_RSI_HIGH:
        rsi_score = 0.5 + (rsi - config.SCORE_RSI_LOW) / (config.SCORE_RSI_HIGH - config.SCORE_RSI_LOW) * 0.5
    else:
        # Overbought: linearly decay from 1.0 at RSI=70 to 0 at RSI=100
        rsi_score = max(0.0, 1.0 - (rsi - config.SCORE_RSI_HIGH) / (100.0 - config.SCORE_RSI_HIGH))

    # --- MACD component (0-1) ---
    if macd_line > macd_signal_val and macd_hist > 0:
        macd_score = 1.0
    elif macd_line > macd_signal_val or macd_hist > 0:
        macd_score = 0.5
    else:
        macd_score = 0.0

    # --- Bollinger Band component (0-1) ---
    band_range = bb_upper - bb_middle
    if band_range > 0 and price >= bb_middle:
        bb_score = min((price - bb_middle) / band_range, 1.0)
    else:
        bb_score = 0.0

    raw = (
        config.SCORE_WEIGHT_PRICE_MOMENTUM * price_score
        + config.SCORE_WEIGHT_VOLUME_SPIKE * volume_score
        + config.SCORE_WEIGHT_RSI * rsi_score
        + config.SCORE_WEIGHT_MACD * macd_score
        + config.SCORE_WEIGHT_BB * bb_score
    )
    return round(raw * 100.0, 2)


def detect_pump(price_change_pct: float, volume_change_pct: float) -> bool:
    """Return True when both the price-change and volume-spike thresholds are met."""
    if price_change_pct != price_change_pct or volume_change_pct != volume_change_pct:
        return False
    return (
        price_change_pct >= config.PUMP_MIN_PRICE_CHANGE_PCT
        and volume_change_pct >= config.PUMP_MIN_VOLUME_SPIKE_PCT
    )


# ---------------------------------------------------------------------------
# Scanning pipeline
# ---------------------------------------------------------------------------

def scan_pair(exchange: ccxt.Exchange, symbol: str) -> Optional[Dict[str, Any]]:
    """Download and analyse one trading pair.

    Returns a signal dictionary or *None* if data is unavailable / insufficient.
    """
    df = fetch_ohlcv(exchange, symbol)
    if df is None or df.empty:
        return None

    closes = df["close"]
    volumes = df["volume"]
    price = float(closes.iloc[-1])

    price_change_pct = compute_price_change(closes)
    volume_change_pct = compute_volume_change(volumes)
    rsi = compute_rsi(closes)
    macd_line, macd_sig, macd_hist = compute_macd(closes)
    bb_upper, bb_middle, bb_lower = compute_bollinger_bands(closes)

    s = score_coin(
        price_change_pct, volume_change_pct, rsi,
        macd_line, macd_sig, macd_hist,
        price, bb_upper, bb_middle,
    )
    is_pump = detect_pump(price_change_pct, volume_change_pct)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "price": price,
        "price_change_pct": price_change_pct,
        "volume_change_pct": volume_change_pct,
        "rsi": rsi,
        "macd": macd_line,
        "macd_signal": macd_sig,
        "macd_hist": macd_hist,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
        "score": s,
        "is_pump": is_pump,
    }


def scan_all_pairs(exchange: ccxt.Exchange) -> List[Dict[str, Any]]:
    """Scan every EUR pair; return list of signal dicts sorted by score DESC."""
    symbols = fetch_eur_pairs(exchange)
    logger.info("Scanning %d EUR pairs …", len(symbols))
    results: List[Dict[str, Any]] = []
    for sym in symbols:
        try:
            sig = scan_pair(exchange, sym)
        except Exception as exc:
            logger.warning("Skipping %s – %s", sym, exc)
            sig = None
        if sig is not None:
            results.append(sig)
        time.sleep(config.REQUEST_DELAY_SECONDS)
    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info("Scan complete – %d pairs processed", len(results))
    return results


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_coins(signals: List[Dict[str, Any]], top_n: int = config.TOP_N_COINS) -> List[Dict[str, Any]]:
    """Return the *top_n* highest-scoring signals (already sorted DESC by caller)."""
    return signals[:top_n]


# ---------------------------------------------------------------------------
# Balance & order helpers
# ---------------------------------------------------------------------------

@retry_on_error()
def get_eur_balance(exchange: ccxt.Exchange) -> float:
    """Return the free EUR balance available for trading."""
    balance = exchange.fetch_balance()
    return float(balance.get("EUR", {}).get("free", 0.0))


def calculate_trade_amount(eur_balance: float, score: float) -> float:
    """Determine EUR amount to risk based on score.

    Higher score → allocate closer to TRADE_BALANCE_MAX_PCT.
    Score is expected in [0, 100]; clamped to that range.
    """
    score_norm = min(max(score, 0.0), 100.0) / 100.0
    pct = config.TRADE_BALANCE_MIN_PCT + (
        config.TRADE_BALANCE_MAX_PCT - config.TRADE_BALANCE_MIN_PCT
    ) * score_norm
    return round(eur_balance * pct, 2)


@retry_on_error()
def place_market_buy(exchange: ccxt.Exchange, symbol: str, amount_eur: float) -> Dict[str, Any]:
    """Place a market buy order for *amount_eur* EUR worth of *symbol*.

    Uses `createMarketBuyOrderWithCost` when available (Binance supports it),
    falling back to a regular cost-based order.
    """
    if hasattr(exchange, "createMarketBuyOrderWithCost"):
        return exchange.createMarketBuyOrderWithCost(symbol, amount_eur)
    return exchange.create_order(symbol, "market", "buy", None, None, {"quoteOrderQty": amount_eur})


@retry_on_error()
def place_oco_sell(
    exchange: ccxt.Exchange,
    symbol: str,
    amount_coin: float,
    take_profit_price: float,
    stop_loss_price: float,
    stop_limit_price: float,
) -> Dict[str, Any]:
    """Place an OCO (One-Cancels-Other) sell order on Binance.

    An OCO pairs a limit sell (take-profit) with a stop-limit sell (stop-loss).
    When one fills or is cancelled the exchange automatically cancels the other.
    """
    return exchange.create_order(
        symbol,
        "STOP_LOSS_LIMIT",
        "sell",
        amount_coin,
        stop_limit_price,
        {
            "stopPrice": stop_loss_price,
            "price": stop_limit_price,
            "type": "OCO",
            "aboveType": "LIMIT_MAKER",
            "abovePrice": take_profit_price,
            "belowType": "STOP_LOSS_LIMIT",
            "belowStopPrice": stop_loss_price,
            "belowPrice": stop_limit_price,
            "quantity": amount_coin,
        },
    )


# ---------------------------------------------------------------------------
# Trade execution
# ---------------------------------------------------------------------------

def execute_trade(
    exchange: ccxt.Exchange,
    signal: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Execute a full trade for one signal: buy + stop-loss + take-profit orders.

    Returns a trade-log dict that includes filled entry price, risk levels, and
    initial status.  Returns *None* on failure (error is logged).
    """
    symbol = signal["symbol"]
    score = signal["score"]
    now_ts = datetime.now(timezone.utc).isoformat()

    try:
        eur_balance = get_eur_balance(exchange)
        if eur_balance <= 0:
            logger.warning("No EUR balance available – skipping trade for %s", symbol)
            return None

        amount_eur = calculate_trade_amount(eur_balance, score)
        logger.info("Trading %s  score=%.1f  EUR=%.2f", symbol, score, amount_eur)

        # --- market buy ---
        buy_order = place_market_buy(exchange, symbol, amount_eur)
        raw_price = buy_order.get("average") or buy_order.get("price")
        if not raw_price:
            raise RuntimeError(
                f"Buy order for {symbol} returned no entry price; "
                "cannot calculate risk levels safely."
            )
        entry_price = float(raw_price)
        amount_coin = float(buy_order.get("filled") or buy_order.get("amount") or (amount_eur / entry_price))

        # --- risk levels ---
        stop_loss_price = round(entry_price * (1.0 - config.STOP_LOSS_PCT), 8)
        # Stop-limit is placed 0.1 % below the stop trigger to ensure fill
        stop_limit_price = round(stop_loss_price * 0.999, 8)
        take_profit_price = round(entry_price * (1.0 + config.TAKE_PROFIT_PCT), 8)

        # --- OCO sell (take-profit & stop-loss, one cancels the other) ---
        try:
            place_oco_sell(
                exchange, symbol, amount_coin,
                take_profit_price, stop_loss_price, stop_limit_price,
            )
            logger.info(
                "  OCO sell placed: TP=%.8f  SL=%.8f",
                take_profit_price, stop_loss_price,
            )
        except Exception as exc:
            logger.error("  Could not place OCO order for %s: %s", symbol, exc)

        trade_record: Dict[str, Any] = {
            "timestamp": now_ts,
            "symbol": symbol,
            "score": score,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "amount_eur": amount_eur,
            "amount_coin": amount_coin,
            "exit_price": "",
            "pnl_eur": "",
            "status": "open",
        }
        log_trade(trade_record)
        logger.info("  Trade logged for %s", symbol)
        return trade_record

    except Exception as exc:
        logger.error("Trade execution failed for %s: %s", symbol, exc)
        error_record: Dict[str, Any] = {
            "timestamp": now_ts,
            "symbol": symbol,
            "score": score,
            "entry_price": signal.get("price", ""),
            "stop_loss_price": "",
            "take_profit_price": "",
            "amount_eur": "",
            "amount_coin": "",
            "exit_price": "",
            "pnl_eur": "",
            "status": f"error: {exc}",
        }
        log_trade(error_record)
        return None


# ---------------------------------------------------------------------------
# Main scan-trade loop
# ---------------------------------------------------------------------------

def run(exchange: Optional[ccxt.Exchange] = None) -> None:
    """Run the bot continuously: scan → rank → trade → sleep → repeat.

    Handles SIGTERM and SIGINT for a clean shutdown so that in-flight work is
    completed before the process exits.
    """
    if exchange is None:
        exchange = create_exchange()

    shutdown = {"requested": False}

    def _handle_signal(signum: int, frame: Any) -> None:  # noqa: ANN001
        logger.info("Shutdown signal received (%s) – finishing current cycle …", signum)
        shutdown["requested"] = True

    _signal.signal(_signal.SIGTERM, _handle_signal)
    _signal.signal(_signal.SIGINT, _handle_signal)

    logger.info("Bot started – quote currency: %s", config.QUOTE_CURRENCY)

    while not shutdown["requested"]:
        try:
            signals = scan_all_pairs(exchange)

            # Log every high-conviction signal
            for sig in signals:
                if sig["score"] >= config.SIGNAL_SCORE_THRESHOLD:
                    log_signal(sig)

            # Rank and trade the top-N coins
            top_coins = rank_coins(signals, config.TOP_N_COINS)
            logger.info(
                "Top %d coins: %s",
                len(top_coins),
                [(c["symbol"], c["score"]) for c in top_coins],
            )
            for sig in top_coins:
                if shutdown["requested"]:
                    break
                execute_trade(exchange, sig)

        except Exception as exc:
            logger.error("Unhandled error in scan loop: %s", exc)

        if not shutdown["requested"]:
            logger.info("Sleeping %ds until next scan …", config.SCAN_INTERVAL_SECONDS)
            # Sleep in small increments so SIGINT is handled promptly
            elapsed = 0.0
            while elapsed < config.SCAN_INTERVAL_SECONDS and not shutdown["requested"]:
                time.sleep(1.0)
                elapsed += 1.0

    logger.info("Bot stopped cleanly.")


if __name__ == "__main__":
    run()
