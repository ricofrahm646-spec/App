"""
Coin scanner and scorer for the Hardcore Growth Mode trading bot.

Scans all EUR trading pairs on the configured exchange, calculates technical
indicators (RSI, MACD, volume spike, short-term price change) and returns a
scored list of coins.

Scoring (max 100 pts):
  RSI < threshold      → 25 pts
  MACD diff > 0        → 25 pts
  Volume spike > 150%  → 25 pts
  Price +2% / 5 min    → 25 pts
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

import ccxt
import pandas as pd

import config


@dataclass
class CoinSignal:
    symbol: str
    score: int
    entry_price: float
    rsi: float
    macd_diff: float
    volume_spike_ratio: float
    price_change_5m: float
    take_profit: float = field(init=False)
    stop_loss: float = field(init=False)

    def __post_init__(self) -> None:
        self.take_profit = round(
            self.entry_price * (1 + config.TAKE_PROFIT_PERCENT), 8
        )
        self.stop_loss = round(
            self.entry_price * (1 - config.STOP_LOSS_PERCENT), 8
        )

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "entry_price": self.entry_price,
            "rsi": round(self.rsi, 2),
            "macd_diff": round(self.macd_diff, 8),
            "volume_spike_ratio": round(self.volume_spike_ratio, 2),
            "price_change_5m": round(self.price_change_5m * 100, 2),
            "take_profit": self.take_profit,
            "stop_loss": self.stop_loss,
        }


class CoinScanner:
    """Fetches OHLCV data and scores all EUR pairs on the exchange."""

    def __init__(self) -> None:
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange: ccxt.Exchange = exchange_class(
            {
                "apiKey": config.API_KEY,
                "secret": config.API_SECRET,
                "enableRateLimit": True,
            }
        )
        self._markets: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scan(self) -> List[CoinSignal]:
        """Return top N scored EUR coins with score >= MIN_SCORE, sorted desc."""
        eur_symbols = self._get_eur_symbols()
        logging.info("Scanning %d EUR pairs…", len(eur_symbols))

        signals: List[CoinSignal] = []
        for symbol in eur_symbols:
            try:
                signal = self._score_symbol(symbol)
                if signal is not None and signal.score >= config.MIN_SCORE:
                    signals.append(signal)
            except ccxt.NetworkError as exc:
                logging.warning("Network error for %s: %s", symbol, exc)
            except ccxt.ExchangeError as exc:
                logging.warning("Exchange error for %s: %s", symbol, exc)
            except Exception as exc:  # noqa: BLE001
                logging.debug("Unexpected error for %s: %s", symbol, exc)

        signals.sort(key=lambda s: s.score, reverse=True)
        top = signals[: config.MAX_TOP_COINS]
        logging.info(
            "Top coins: %s",
            [(s.symbol, s.score) for s in top],
        )
        return top

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_eur_symbols(self) -> List[str]:
        if self._markets is None:
            self._markets = self.exchange.load_markets()
        return [
            s
            for s, m in self._markets.items()
            if m.get("quote") == config.QUOTE_CURRENCY
            and m.get("active", True)
        ]

    def _score_symbol(self, symbol: str) -> Optional[CoinSignal]:
        ohlcv = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=config.CANDLE_TIMEFRAME,
            limit=config.CANDLE_LIMIT,
        )
        if len(ohlcv) < 30:
            return None

        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        score = 0

        # --- RSI ---
        rsi = self._rsi(df["close"])
        if rsi < config.RSI_THRESHOLD:
            score += 25

        # --- MACD diff ---
        macd_diff = self._macd_diff(df["close"])
        if macd_diff > 0:
            score += 25

        # --- Volume spike ---
        avg_vol = df["volume"].iloc[:-1].mean()
        last_vol = df["volume"].iloc[-1]
        spike_ratio = last_vol / avg_vol if avg_vol > 0 else 0
        if spike_ratio >= config.VOLUME_SPIKE_RATIO:
            score += 25

        # --- Price change in last ~5 candles (5 min on 1m timeframe) ---
        if len(df) >= 6:
            price_5m_ago = df["close"].iloc[-6]
            last_price = df["close"].iloc[-1]
            price_change = (last_price - price_5m_ago) / price_5m_ago
        else:
            price_change = 0.0

        if price_change >= config.PRICE_INCREASE_THRESHOLD:
            score += 25

        return CoinSignal(
            symbol=symbol,
            score=score,
            entry_price=last_price,
            rsi=rsi,
            macd_diff=macd_diff,
            volume_spike_ratio=spike_ratio,
            price_change_5m=price_change,
        )

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        last_gain = float(avg_gain.iloc[-1])
        last_loss = float(avg_loss.iloc[-1])
        if last_loss == 0:
            return 100.0 if last_gain > 0 else 50.0
        rs = last_gain / last_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _macd_diff(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        diff = macd_line - signal_line
        return float(diff.iloc[-1])
