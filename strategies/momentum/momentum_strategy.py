"""Momentum trading strategy using RSI + MACD confirmation."""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal, Direction

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """Trades in the direction of strong price momentum using RSI + MACD confluence."""

    @property
    def name(self) -> str:
        return "Momentum Strategy"

    @property
    def description(self) -> str:
        return "RSI + MACD momentum confluence with ATR-based SL/TP"

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "rsi_upper": 60.0,
            "rsi_lower": 40.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "atr_period": 14,
            "sl_atr_mult": 1.5,
            "tp_atr_mult": 3.0,
        }

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(series: pd.Series, fast: int, slow: int, signal: int):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        min_len = max(p["macd_slow"] + p["macd_signal"], p["rsi_period"], p["atr_period"]) + 5

        if len(data) < min_len:
            return Signal(direction=Direction.NONE, confidence=0.0)

        close = data["close"]
        high = data["high"]
        low = data["low"]

        rsi = self._rsi(close, p["rsi_period"])
        _, _, histogram = self._macd(close, p["macd_fast"], p["macd_slow"], p["macd_signal"])

        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(p["atr_period"]).mean()

        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        current_atr = atr.iloc[-1]
        current_close = close.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            return Signal(direction=Direction.NONE, confidence=0.0)

        bullish_rsi = current_rsi > p["rsi_upper"] and prev_rsi <= p["rsi_upper"]
        bullish_macd = current_hist > 0 and prev_hist <= 0

        if bullish_rsi and bullish_macd:
            sl = current_close - current_atr * p["sl_atr_mult"]
            tp = current_close + current_atr * p["tp_atr_mult"]
            confidence = min(0.9, 0.5 + abs(current_hist) / current_atr * 0.15)
            return Signal(
                direction=Direction.BUY,
                confidence=round(confidence, 3),
                entry_price=current_close,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        bearish_rsi = current_rsi < p["rsi_lower"] and prev_rsi >= p["rsi_lower"]
        bearish_macd = current_hist < 0 and prev_hist >= 0

        if bearish_rsi and bearish_macd:
            sl = current_close + current_atr * p["sl_atr_mult"]
            tp = current_close - current_atr * p["tp_atr_mult"]
            confidence = min(0.9, 0.5 + abs(current_hist) / current_atr * 0.15)
            return Signal(
                direction=Direction.SELL,
                confidence=round(confidence, 3),
                entry_price=current_close,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        return Signal(direction=Direction.NONE, confidence=0.0)
