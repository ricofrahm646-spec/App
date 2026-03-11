#!/usr/bin/env python3
"""
Binance EUR Trading Bot
=======================
Scans all EUR trading pairs on Binance, calculates technical indicators
(RSI, MACD, Bollinger Bands, volume change), detects momentum pumps, scores
each pair, and logs high-scoring candidates to a CSV file.

Usage
-----
    python trading_bot.py

The bot runs continuously, scanning every SCAN_INTERVAL_SECONDS (configured in
config.py).  Press Ctrl-C to stop.
"""

from __future__ import annotations

import csv
import logging
import os
import time
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import ccxt
import numpy as np
import pandas as pd

import config

# ── Logging setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Data containers ────────────────────────────────────────────────────────────

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


@dataclass
class Indicators:
    """Computed technical indicators for a single symbol."""

    symbol: str
    price: float = 0.0
    price_change_pct: float = 0.0   # % change over last candle
    volume_change_pct: float = 0.0  # % change vs. rolling baseline
    rsi: float = float("nan")
    macd: float = float("nan")
    macd_signal: float = float("nan")
    macd_hist: float = float("nan")
    bb_upper: float = float("nan")
    bb_middle: float = float("nan")
    bb_lower: float = float("nan")
    score: float = 0.0
    is_pump: bool = False


@dataclass
class TradeSignal:
    """A trade signal with score above SCORE_THRESHOLD."""

    timestamp: str
    symbol: str
    price: float
    price_change_pct: float
    volume_change_pct: float
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    score: float
    is_pump: bool


# ── Technical indicator calculations ──────────────────────────────────────────

def calculate_rsi(prices: pd.Series, period: int = config.RSI_PERIOD) -> float:
    """Return the most recent RSI value for *prices*.

    Uses Wilder's smoothed EMA method (equivalent to RMA / Wilder MA).
    Returns NaN when there are fewer candles than the period.
    """
    if len(prices) < period + 1:
        return float("nan")

    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Wilder smoothing (ewm with alpha = 1/period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # When avg_loss is 0 (only gains), rs = inf → RSI = 100.
    # Suppress pandas warning about dividing by zero; inf is the correct result.
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi.iloc[-1])


def calculate_macd(
    prices: pd.Series,
    fast: int = config.MACD_FAST,
    slow: int = config.MACD_SLOW,
    signal: int = config.MACD_SIGNAL,
) -> Tuple[float, float, float]:
    """Return (macd_line, signal_line, histogram) for the most recent candle."""
    if len(prices) < slow + signal:
        nan = float("nan")
        return nan, nan, nan

    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = config.BB_PERIOD,
    std_dev: float = config.BB_STD_DEV,
) -> Tuple[float, float, float]:
    """Return (upper, middle, lower) Bollinger Bands for the most recent candle."""
    if len(prices) < period:
        nan = float("nan")
        return nan, nan, nan

    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std(ddof=0)
    upper = sma + std_dev * std
    lower = sma - std_dev * std

    return float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1])


def calculate_volume_change(
    volumes: pd.Series,
    lookback: int = config.VOLUME_LOOKBACK,
    baseline: int = config.VOLUME_BASELINE,
) -> float:
    """Return % change between recent average volume and the baseline average.

    A value of 150 means volume is 150 % *higher* than the baseline.
    """
    required = lookback + baseline
    if len(volumes) < required:
        return 0.0

    recent_avg = volumes.iloc[-lookback:].mean()
    baseline_avg = volumes.iloc[-(lookback + baseline):-lookback].mean()

    if baseline_avg == 0:
        return 0.0

    return ((recent_avg - baseline_avg) / baseline_avg) * 100.0


def calculate_price_change(closes: pd.Series) -> float:
    """Return % price change between the last two closed candles."""
    if len(closes) < 2:
        return 0.0
    prev = closes.iloc[-2]
    curr = closes.iloc[-1]
    if prev == 0:
        return 0.0
    return ((curr - prev) / prev) * 100.0


# ── Scoring ────────────────────────────────────────────────────────────────────

def score_price_momentum(price_change_pct: float) -> float:
    """Score 0–100 based on percentage price change.

    0 % → 0 points, 2 % → 50 points, ≥ 5 % → 100 points (linear capped).
    """
    if price_change_pct <= 0:
        return 0.0
    return min(price_change_pct / 5.0 * 100.0, 100.0)


def score_volume_spike(volume_change_pct: float) -> float:
    """Score 0–100 based on volume % increase.

    0 % → 0 points, 150 % → 50 points, ≥ 300 % → 100 points (linear capped).
    """
    if volume_change_pct <= 0:
        return 0.0
    return min(volume_change_pct / 300.0 * 100.0, 100.0)


def score_rsi(rsi: float) -> float:
    """Score 0–100 based on RSI value.

    Optimal momentum range is 50–70.  Returns 100 for that range and tapers off.
    """
    if np.isnan(rsi):
        return 0.0
    if 50.0 <= rsi <= 70.0:
        return 100.0
    if 40.0 <= rsi < 50.0:
        return (rsi - 40.0) / 10.0 * 100.0
    if 70.0 < rsi <= 80.0:
        return (80.0 - rsi) / 10.0 * 100.0
    return 0.0


def score_macd(macd: float, macd_signal: float, macd_hist: float) -> float:
    """Score 0–100 based on MACD position.

    MACD > signal *and* positive histogram → 100.
    MACD > signal only → 50.
    Otherwise → 0.
    """
    if np.isnan(macd) or np.isnan(macd_signal):
        return 0.0
    if macd > macd_signal and macd_hist > 0:
        return 100.0
    if macd > macd_signal:
        return 50.0
    return 0.0


def score_bollinger(price: float, bb_upper: float, bb_middle: float) -> float:
    """Score 0–100 based on price position within Bollinger Bands.

    Price above middle band → 50.  Price above upper band → 100.
    """
    if np.isnan(bb_middle) or np.isnan(bb_upper):
        return 0.0
    if price >= bb_upper:
        return 100.0
    if price >= bb_middle:
        return 50.0
    return 0.0


def compute_score(ind: Indicators) -> float:
    """Compute the composite momentum score (0–100) for a pair."""
    s_price = score_price_momentum(ind.price_change_pct)
    s_volume = score_volume_spike(ind.volume_change_pct)
    s_rsi = score_rsi(ind.rsi)
    s_macd = score_macd(ind.macd, ind.macd_signal, ind.macd_hist)
    s_bb = score_bollinger(ind.price, ind.bb_upper, ind.bb_middle)

    total = (
        s_price * config.SCORE_WEIGHT_PRICE
        + s_volume * config.SCORE_WEIGHT_VOLUME
        + s_rsi * config.SCORE_WEIGHT_RSI
        + s_macd * config.SCORE_WEIGHT_MACD
        + s_bb * config.SCORE_WEIGHT_BB
    ) / 100.0  # weights sum to 100, raw scores are 0-100

    return round(total, 2)


# ── Core analysis ──────────────────────────────────────────────────────────────

def analyze_symbol(
    exchange: ccxt.Exchange, symbol: str
) -> Optional[Indicators]:
    """Fetch OHLCV data for *symbol* and compute all indicators.

    Returns ``None`` when data cannot be retrieved or is insufficient.
    """
    try:
        raw = exchange.fetch_ohlcv(
            symbol, timeframe=config.TIMEFRAME, limit=config.OHLCV_LIMIT
        )
    except (ccxt.NetworkError, ccxt.ExchangeError, ccxt.BaseError) as exc:
        logger.warning("Could not fetch OHLCV for %s: %s", symbol, exc)
        return None

    if not raw or len(raw) < config.BB_PERIOD + config.VOLUME_LOOKBACK + config.VOLUME_BASELINE:
        logger.debug("Insufficient data for %s (%d candles)", symbol, len(raw) if raw else 0)
        return None

    df = pd.DataFrame(raw, columns=OHLCV_COLUMNS)
    closes = df["close"].astype(float)
    volumes = df["volume"].astype(float)

    ind = Indicators(symbol=symbol)
    ind.price = float(closes.iloc[-1])
    ind.price_change_pct = calculate_price_change(closes)
    ind.volume_change_pct = calculate_volume_change(volumes)
    ind.rsi = calculate_rsi(closes)
    ind.macd, ind.macd_signal, ind.macd_hist = calculate_macd(closes)
    ind.bb_upper, ind.bb_middle, ind.bb_lower = calculate_bollinger_bands(closes)
    ind.score = compute_score(ind)
    ind.is_pump = (
        ind.price_change_pct >= config.PRICE_INCREASE_THRESHOLD
        and ind.volume_change_pct >= config.VOLUME_SPIKE_THRESHOLD
    )

    return ind


# ── CSV logging ────────────────────────────────────────────────────────────────

CSV_HEADERS = [f.name for f in fields(TradeSignal)]


def _ensure_csv(path: str) -> None:
    """Create the CSV file with headers if it does not already exist."""
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
            writer.writeheader()


def log_trade_signal(signal: TradeSignal, path: str = config.CSV_FILE) -> None:
    """Append a trade signal row to the CSV log."""
    _ensure_csv(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
        writer.writerow(
            {f.name: getattr(signal, f.name) for f in fields(TradeSignal)}
        )


def indicators_to_signal(ind: Indicators) -> TradeSignal:
    """Convert an :class:`Indicators` instance into a :class:`TradeSignal`."""
    return TradeSignal(
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol=ind.symbol,
        price=ind.price,
        price_change_pct=round(ind.price_change_pct, 4),
        volume_change_pct=round(ind.volume_change_pct, 4),
        rsi=round(ind.rsi, 4) if not np.isnan(ind.rsi) else float("nan"),
        macd=round(ind.macd, 8) if not np.isnan(ind.macd) else float("nan"),
        macd_signal=round(ind.macd_signal, 8) if not np.isnan(ind.macd_signal) else float("nan"),
        macd_hist=round(ind.macd_hist, 8) if not np.isnan(ind.macd_hist) else float("nan"),
        bb_upper=round(ind.bb_upper, 8) if not np.isnan(ind.bb_upper) else float("nan"),
        bb_middle=round(ind.bb_middle, 8) if not np.isnan(ind.bb_middle) else float("nan"),
        bb_lower=round(ind.bb_lower, 8) if not np.isnan(ind.bb_lower) else float("nan"),
        score=ind.score,
        is_pump=ind.is_pump,
    )


# ── Main scanning loop ─────────────────────────────────────────────────────────

def get_eur_pairs(exchange: ccxt.Exchange) -> List[str]:
    """Return all active EUR-quoted spot symbols available on the exchange."""
    try:
        markets = exchange.load_markets()
    except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
        logger.error("Failed to load markets: %s", exc)
        return []

    pairs = [
        symbol
        for symbol, market in markets.items()
        if market.get("quote") == config.QUOTE_CURRENCY
        and market.get("active", True)
        and market.get("spot", True)
    ]
    logger.info("Found %d %s pairs", len(pairs), config.QUOTE_CURRENCY)
    return sorted(pairs)


def run_scan(exchange: ccxt.Exchange) -> List[TradeSignal]:
    """Scan all EUR pairs once, returning signals with score > SCORE_THRESHOLD."""
    pairs = get_eur_pairs(exchange)
    if not pairs:
        logger.warning("No EUR pairs found – skipping scan.")
        return []

    logger.info("Scanning %d pairs …", len(pairs))
    signals: List[TradeSignal] = []

    for symbol in pairs:
        ind = analyze_symbol(exchange, symbol)
        if ind is None:
            continue

        logger.debug(
            "%s | price=%.6f | Δprice=%.2f%% | Δvol=%.1f%% | RSI=%.1f | score=%.1f | pump=%s",
            ind.symbol,
            ind.price,
            ind.price_change_pct,
            ind.volume_change_pct,
            ind.rsi if not np.isnan(ind.rsi) else -1,
            ind.score,
            ind.is_pump,
        )

        if ind.score >= config.SCORE_THRESHOLD:
            signal = indicators_to_signal(ind)
            signals.append(signal)
            log_trade_signal(signal)
            logger.info(
                "🚀 SIGNAL | %s | score=%.1f | pump=%s | Δprice=%.2f%% | Δvol=%.1f%%",
                signal.symbol,
                signal.score,
                signal.is_pump,
                signal.price_change_pct,
                signal.volume_change_pct,
            )

        time.sleep(config.REQUEST_DELAY_SECONDS)

    logger.info(
        "Scan complete – %d / %d pairs scored ≥ %d",
        len(signals),
        len(pairs),
        config.SCORE_THRESHOLD,
    )
    return signals


def main() -> None:
    """Entry-point: initialise the exchange and run the scanning loop."""
    logger.info("Starting Binance EUR Trading Bot")
    logger.info(
        "Config: interval=%ds | price_threshold=%.1f%% | volume_threshold=%.1f%% | score_threshold=%d",
        config.SCAN_INTERVAL_SECONDS,
        config.PRICE_INCREASE_THRESHOLD,
        config.VOLUME_SPIKE_THRESHOLD,
        config.SCORE_THRESHOLD,
    )

    exchange = ccxt.binance(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
    )

    _ensure_csv(config.CSV_FILE)

    while True:
        scan_start = time.monotonic()

        try:
            run_scan(exchange)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error during scan: %s", exc, exc_info=True)

        elapsed = time.monotonic() - scan_start
        wait = max(0.0, config.SCAN_INTERVAL_SECONDS - elapsed)
        if wait > 0:
            logger.info("Next scan in %.0f seconds …", wait)
            time.sleep(wait)


if __name__ == "__main__":
    main()
