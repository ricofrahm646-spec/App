"""
JARVIS Trading OS - Market Data Provider
Real-time price feeds, multi-timeframe aggregation, trading session detection,
spread monitoring, and volatility calculation.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional

import MetaTrader5 as mt5

from mt5.connector.mt5_client import MT5Client
from mt5.utils.helpers import (
    pip_value,
    price_to_pips,
    resolve_timeframe,
    utc_now,
)

logger = logging.getLogger("jarvis.mt5.market_data")

PRICE_FEED_INTERVAL_S = 0.5
SPREAD_HISTORY_SIZE = 300  # ~2.5 min at 0.5 s


class TradingSession(str, Enum):
    """Major forex trading sessions (UTC hours)."""
    SYDNEY = "Sydney"
    TOKYO = "Tokyo"
    LONDON = "London"
    NEW_YORK = "New York"
    OFF_HOURS = "Off Hours"


SESSION_SCHEDULE_UTC: dict[TradingSession, tuple[int, int]] = {
    TradingSession.SYDNEY: (21, 6),    # 21:00 – 06:00 UTC
    TradingSession.TOKYO: (0, 9),      # 00:00 – 09:00 UTC
    TradingSession.LONDON: (7, 16),    # 07:00 – 16:00 UTC
    TradingSession.NEW_YORK: (12, 21), # 12:00 – 21:00 UTC
}


@dataclass
class PriceTick:
    """A single price observation."""
    symbol: str
    bid: float
    ask: float
    spread_points: int
    spread_pips: float
    timestamp: datetime


@dataclass
class VolatilityInfo:
    """Volatility metrics for a symbol/timeframe combination."""
    symbol: str
    timeframe: str
    atr: float
    atr_pips: float
    stddev: float
    stddev_pips: float
    high_low_range_pips: float
    bars_used: int


@dataclass
class SpreadStats:
    """Running spread statistics for a symbol."""
    symbol: str
    current: float
    average: float
    minimum: float
    maximum: float
    sample_count: int


class MarketDataProvider:
    """Centralised market data service with real-time feeds and analytics.

    Runs a background thread that continuously polls prices for subscribed
    symbols, computes spread statistics, and exposes convenience methods for
    multi-timeframe data, session detection, and volatility.
    """

    def __init__(
        self,
        client: MT5Client,
        poll_interval: float = PRICE_FEED_INTERVAL_S,
        on_tick: Optional[Callable[[PriceTick], None]] = None,
    ) -> None:
        """Initialise the market data provider.

        Args:
            client: Connected ``MT5Client``.
            poll_interval: Seconds between price polls.
            on_tick: Optional callback invoked on every new tick.
        """
        self._client = client
        self._poll_interval = poll_interval
        self._on_tick = on_tick

        self._subscriptions: set[str] = set()
        self._latest_prices: dict[str, PriceTick] = {}
        self._spread_history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=SPREAD_HISTORY_SIZE)
        )
        self._active = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, *symbols: str) -> None:
        """Add symbols to the live price feed.

        Args:
            symbols: One or more instrument names.
        """
        for sym in symbols:
            upper = sym.upper().strip()
            self._subscriptions.add(upper)
            try:
                mt5.symbol_select(upper, True)
            except Exception as exc:
                logger.warning("Could not select %s in Market Watch: %s", upper, exc)
        logger.info("Subscribed: %s (total %d)", symbols, len(self._subscriptions))

    def unsubscribe(self, *symbols: str) -> None:
        """Remove symbols from the live price feed."""
        for sym in symbols:
            self._subscriptions.discard(sym.upper().strip())
        logger.info("Unsubscribed: %s (remaining %d)", symbols, len(self._subscriptions))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background price-feed thread."""
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(
            target=self._feed_loop, daemon=True, name="jarvis-market-data"
        )
        self._thread.start()
        logger.info("Market data feed started (interval=%.2fs)", self._poll_interval)

    def stop(self) -> None:
        """Stop the price-feed thread."""
        self._active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._poll_interval * 3)
        logger.info("Market data feed stopped")

    @property
    def is_running(self) -> bool:
        return self._active

    # ------------------------------------------------------------------
    # Real-time price feed
    # ------------------------------------------------------------------

    def _feed_loop(self) -> None:
        """Continuously poll prices for subscribed symbols."""
        while self._active:
            try:
                if not self._client.is_connected():
                    time.sleep(self._poll_interval * 2)
                    continue

                for symbol in list(self._subscriptions):
                    self._poll_symbol(symbol)

            except Exception as exc:
                logger.error("Feed loop error: %s", exc)
            time.sleep(self._poll_interval)

    def _poll_symbol(self, symbol: str) -> None:
        """Fetch the latest tick for a single symbol and update caches."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return

        info = mt5.symbol_info(symbol)
        if info is None:
            return

        pv = pip_value(symbol, info.point, info.digits)
        spread_pips = (info.spread * info.point) / pv if pv > 0 else 0.0

        price_tick = PriceTick(
            symbol=symbol,
            bid=tick.bid,
            ask=tick.ask,
            spread_points=info.spread,
            spread_pips=spread_pips,
            timestamp=datetime.fromtimestamp(tick.time, tz=timezone.utc),
        )

        with self._lock:
            self._latest_prices[symbol] = price_tick
            self._spread_history[symbol].append(spread_pips)

        if self._on_tick:
            try:
                self._on_tick(price_tick)
            except Exception as exc:
                logger.error("on_tick callback error for %s: %s", symbol, exc)

    # ------------------------------------------------------------------
    # Latest price access
    # ------------------------------------------------------------------

    def get_latest_price(self, symbol: str) -> Optional[PriceTick]:
        """Return the most recently cached tick for *symbol*."""
        with self._lock:
            return self._latest_prices.get(symbol.upper())

    def get_all_latest_prices(self) -> dict[str, PriceTick]:
        """Return a snapshot of latest prices for all subscribed symbols."""
        with self._lock:
            return dict(self._latest_prices)

    # ------------------------------------------------------------------
    # Multi-timeframe OHLCV
    # ------------------------------------------------------------------

    def get_multi_timeframe(
        self,
        symbol: str,
        timeframes: list[str | int],
        count: int = 100,
    ) -> dict[str, list[dict[str, Any]]]:
        """Retrieve OHLCV data across multiple timeframes.

        Args:
            symbol: Instrument name.
            timeframes: List of timeframe strings or MT5 constants.
            count: Number of bars per timeframe.

        Returns:
            Dict mapping timeframe label to list of bar dicts.
        """
        result: dict[str, list[dict[str, Any]]] = {}
        for tf in timeframes:
            label = tf if isinstance(tf, str) else str(tf)
            try:
                bars = self._client.get_ohlcv(symbol, tf, count)
                result[label] = bars
            except Exception as exc:
                logger.error("Multi-TF fetch error for %s %s: %s", symbol, label, exc)
                result[label] = []
        return result

    # ------------------------------------------------------------------
    # Trading session detection
    # ------------------------------------------------------------------

    @staticmethod
    def get_active_sessions(dt: Optional[datetime] = None) -> list[TradingSession]:
        """Determine which trading sessions are active at a given UTC time.

        Args:
            dt: A timezone-aware datetime (defaults to now UTC).

        Returns:
            List of active ``TradingSession`` values.
        """
        if dt is None:
            dt = utc_now()
        hour = dt.hour
        active: list[TradingSession] = []
        for session, (start, end) in SESSION_SCHEDULE_UTC.items():
            if start < end:
                if start <= hour < end:
                    active.append(session)
            else:
                if hour >= start or hour < end:
                    active.append(session)
        if not active:
            active.append(TradingSession.OFF_HOURS)
        return active

    @staticmethod
    def is_session_overlap(dt: Optional[datetime] = None) -> bool:
        """Return True when two or more major sessions overlap.

        Session overlaps typically see the highest liquidity and volatility.
        """
        sessions = MarketDataProvider.get_active_sessions(dt)
        real = [s for s in sessions if s != TradingSession.OFF_HOURS]
        return len(real) >= 2

    @staticmethod
    def next_session_open(session: TradingSession, dt: Optional[datetime] = None) -> datetime:
        """Return the next opening time for *session* relative to *dt*.

        Args:
            session: Target trading session.
            dt: Reference time (defaults to now UTC).

        Returns:
            Next opening datetime (UTC, timezone-aware).
        """
        if dt is None:
            dt = utc_now()
        start_hour, _ = SESSION_SCHEDULE_UTC[session]
        candidate = dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if candidate <= dt:
            candidate += timedelta(days=1)
        return candidate

    # ------------------------------------------------------------------
    # Spread monitoring
    # ------------------------------------------------------------------

    def get_spread_stats(self, symbol: str) -> SpreadStats:
        """Return running spread statistics for *symbol*.

        Args:
            symbol: Instrument name.

        Returns:
            ``SpreadStats`` dataclass.
        """
        with self._lock:
            history = list(self._spread_history.get(symbol.upper(), []))
            latest = self._latest_prices.get(symbol.upper())

        if not history:
            current = latest.spread_pips if latest else 0.0
            return SpreadStats(
                symbol=symbol,
                current=current,
                average=current,
                minimum=current,
                maximum=current,
                sample_count=0,
            )

        return SpreadStats(
            symbol=symbol,
            current=history[-1],
            average=sum(history) / len(history),
            minimum=min(history),
            maximum=max(history),
            sample_count=len(history),
        )

    def is_spread_acceptable(self, symbol: str, max_pips: float) -> bool:
        """Return True if the current spread is within the acceptable range.

        Args:
            symbol: Instrument name.
            max_pips: Maximum allowed spread in pips.
        """
        stats = self.get_spread_stats(symbol)
        return stats.current <= max_pips

    # ------------------------------------------------------------------
    # Volatility calculation
    # ------------------------------------------------------------------

    def calculate_volatility(
        self,
        symbol: str,
        timeframe: str | int = "H1",
        period: int = 14,
    ) -> VolatilityInfo:
        """Compute ATR and standard-deviation-based volatility.

        Args:
            symbol: Instrument name.
            timeframe: Timeframe for the bars (string or MT5 constant).
            period: Look-back period in bars for ATR / stdev.

        Returns:
            ``VolatilityInfo`` with ATR, stdev, and H-L range in both
            price and pip units.
        """
        bars = self._client.get_ohlcv(symbol, timeframe, count=period + 1)
        if len(bars) < 2:
            return VolatilityInfo(
                symbol=symbol,
                timeframe=str(timeframe),
                atr=0.0,
                atr_pips=0.0,
                stddev=0.0,
                stddev_pips=0.0,
                high_low_range_pips=0.0,
                bars_used=0,
            )

        sym_info = self._client.get_symbol_info(symbol)
        pv = pip_value(symbol, sym_info.point, sym_info.digits)

        true_ranges: list[float] = []
        closes: list[float] = []
        hl_ranges: list[float] = []

        for i in range(1, len(bars)):
            high = bars[i]["high"]
            low = bars[i]["low"]
            prev_close = bars[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
            closes.append(bars[i]["close"])
            hl_ranges.append(high - low)

        atr = sum(true_ranges[-period:]) / min(period, len(true_ranges))

        if len(closes) >= 2:
            mean_close = sum(closes) / len(closes)
            variance = sum((c - mean_close) ** 2 for c in closes) / len(closes)
            stddev = math.sqrt(variance)
        else:
            stddev = 0.0

        avg_hl = sum(hl_ranges[-period:]) / min(period, len(hl_ranges)) if hl_ranges else 0.0

        def to_pips(price_delta: float) -> float:
            return price_to_pips(symbol, price_delta, sym_info.point, sym_info.digits)

        return VolatilityInfo(
            symbol=symbol,
            timeframe=str(timeframe),
            atr=atr,
            atr_pips=to_pips(atr),
            stddev=stddev,
            stddev_pips=to_pips(stddev),
            high_low_range_pips=to_pips(avg_hl),
            bars_used=len(true_ranges),
        )

    # ------------------------------------------------------------------
    # Convenience: full symbol summary
    # ------------------------------------------------------------------

    def symbol_summary(self, symbol: str) -> dict[str, Any]:
        """Return a comprehensive snapshot of a symbol's market state.

        Combines price, spread, session, and volatility data into a single
        dict suitable for dashboard rendering or strategy input.
        """
        price = self.get_latest_price(symbol)
        spread = self.get_spread_stats(symbol)
        sessions = self.get_active_sessions()
        overlap = self.is_session_overlap()

        try:
            vol = self.calculate_volatility(symbol, "H1", 14)
        except Exception:
            vol = None

        return {
            "symbol": symbol,
            "bid": price.bid if price else None,
            "ask": price.ask if price else None,
            "spread_pips": spread.current,
            "spread_avg_pips": spread.average,
            "active_sessions": [s.value for s in sessions],
            "session_overlap": overlap,
            "atr_h1_pips": vol.atr_pips if vol else None,
            "volatility_stddev_pips": vol.stddev_pips if vol else None,
            "timestamp": price.timestamp.isoformat() if price else None,
        }
