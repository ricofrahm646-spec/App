"""
Momentum Strategy: MACD + RSI + Price Action.

Identifies strong momentum moves using MACD crossovers confirmed by
RSI momentum direction and bullish/bearish price action patterns.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.implementations.base_strategy import (
    BaseStrategy,
    Signal,
    SLTPLevels,
)


class MomentumStrategy(BaseStrategy):
    """Momentum strategy using MACD crossover, RSI trend, and price action.

    Entry logic:
        - BUY: MACD line crosses above signal line, MACD histogram positive
          and increasing, RSI above 50 and rising, bullish price action
          (close > open for last N bars).
        - SELL: MACD line crosses below signal line, MACD histogram negative
          and decreasing, RSI below 50 and falling, bearish price action.

    Exit: ATR-based dynamic SL/TP with wider TP for momentum continuation.
    """

    def __init__(
        self,
        name: str = "Momentum_MACD_RSI",
        timeframe: str = "H1",
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        rsi_period: int = 14,
        rsi_center: float = 50.0,
        price_action_bars: int = 3,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 3.0,
        require_histogram_increase: bool = True,
    ) -> None:
        super().__init__(name, timeframe)
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.rsi_center = rsi_center
        self.price_action_bars = price_action_bars
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.require_histogram_increase = require_histogram_increase

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        min_needed = max(self.macd_slow, self.rsi_period) + self.macd_signal + 5
        if len(data) < min_needed:
            return Signal.HOLD

        close = data["close"]
        opens = data["open"]

        macd_line, signal_line, histogram = self.macd(
            close, self.macd_fast, self.macd_slow, self.macd_signal
        )
        rsi_val = self.rsi(close, self.rsi_period)

        curr_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        curr_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        curr_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        curr_rsi = rsi_val.iloc[-1]
        prev_rsi = rsi_val.iloc[-2]

        if any(np.isnan(v) for v in [curr_macd, curr_signal, curr_hist, curr_rsi]):
            return Signal.HOLD

        macd_cross_up = prev_macd <= prev_signal and curr_macd > curr_signal
        macd_cross_down = prev_macd >= prev_signal and curr_macd < curr_signal

        hist_increasing = curr_hist > prev_hist
        hist_decreasing = curr_hist < prev_hist
        if not self.require_histogram_increase:
            hist_increasing = True
            hist_decreasing = True

        rsi_bullish = curr_rsi > self.rsi_center and curr_rsi > prev_rsi
        rsi_bearish = curr_rsi < self.rsi_center and curr_rsi < prev_rsi

        bullish_pa = self._bullish_price_action(close, opens)
        bearish_pa = self._bearish_price_action(close, opens)

        if macd_cross_up and curr_hist > 0 and hist_increasing and rsi_bullish and bullish_pa:
            return Signal.BUY

        if macd_cross_down and curr_hist < 0 and hist_decreasing and rsi_bearish and bearish_pa:
            return Signal.SELL

        return Signal.HOLD

    def calculate_sl_tp(self, signal: Signal, data: pd.DataFrame) -> SLTPLevels:
        atr_val = self.atr(data, self.atr_period)
        current_atr = atr_val.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            current_atr = data["close"].iloc[-1] * 0.002

        sl = current_atr * self.sl_atr_mult
        tp = current_atr * self.tp_atr_mult

        return SLTPLevels(stop_loss=sl, take_profit=tp)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timeframe": self.timeframe,
            "macd_fast": self.macd_fast,
            "macd_slow": self.macd_slow,
            "macd_signal": self.macd_signal,
            "rsi_period": self.rsi_period,
            "rsi_center": self.rsi_center,
            "price_action_bars": self.price_action_bars,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
            "tp_atr_mult": self.tp_atr_mult,
            "require_histogram_increase": self.require_histogram_increase,
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        min_needed = max(self.macd_slow, self.rsi_period) + self.macd_signal + 10
        if len(data) < min_needed:
            return False

        atr_val = self.atr(data, self.atr_period)
        if np.isnan(atr_val.iloc[-1]):
            return False

        close = data["close"]
        macd_line, signal_line, histogram = self.macd(
            close, self.macd_fast, self.macd_slow, self.macd_signal
        )
        if np.isnan(macd_line.iloc[-1]):
            return False

        return True

    def _bullish_price_action(self, close: pd.Series, opens: pd.Series) -> bool:
        """Check if recent bars show bullish price action (majority bullish candles)."""
        bullish_count = 0
        for i in range(1, min(self.price_action_bars + 1, len(close))):
            if close.iloc[-i] > opens.iloc[-i]:
                bullish_count += 1

        return bullish_count >= (self.price_action_bars + 1) // 2

    def _bearish_price_action(self, close: pd.Series, opens: pd.Series) -> bool:
        """Check if recent bars show bearish price action (majority bearish candles)."""
        bearish_count = 0
        for i in range(1, min(self.price_action_bars + 1, len(close))):
            if close.iloc[-i] < opens.iloc[-i]:
                bearish_count += 1

        return bearish_count >= (self.price_action_bars + 1) // 2

    def _get_min_bars(self) -> int:
        return max(self.macd_slow + self.macd_signal, self.rsi_period, self.atr_period) + 10
