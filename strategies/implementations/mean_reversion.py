"""
Mean Reversion Strategy: Bollinger Bands + RSI.

Identifies overbought/oversold conditions when price deviates significantly
from its mean, entering counter-trend trades expecting a return to the mean.
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


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands and RSI confirmation.

    Entry logic:
        - BUY: Price touches/crosses below lower Bollinger Band and reverses,
          RSI is in oversold territory (< rsi_oversold).
        - SELL: Price touches/crosses above upper Bollinger Band and reverses,
          RSI is in overbought territory (> rsi_overbought).

    Exit: TP at middle Bollinger Band, fixed SL beyond the band.
    """

    def __init__(
        self,
        name: str = "MeanReversion_BB_RSI",
        timeframe: str = "H1",
        bb_period: int = 20,
        bb_deviation: float = 2.0,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        sl_bb_mult: float = 0.5,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
    ) -> None:
        super().__init__(name, timeframe)
        self.bb_period = bb_period
        self.bb_deviation = bb_deviation
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.sl_bb_mult = sl_bb_mult
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < max(self.bb_period, self.rsi_period) + 5:
            return Signal.HOLD

        close = data["close"]
        upper, middle, lower = self.bollinger_bands(close, self.bb_period, self.bb_deviation)
        rsi_val = self.rsi(close, self.rsi_period)

        curr_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        curr_lower = lower.iloc[-1]
        prev_lower = lower.iloc[-2]
        curr_upper = upper.iloc[-1]
        prev_upper = upper.iloc[-2]
        curr_rsi = rsi_val.iloc[-1]

        if np.isnan(curr_rsi) or np.isnan(curr_lower) or np.isnan(curr_upper):
            return Signal.HOLD

        if prev_close <= prev_lower and curr_close > curr_lower and curr_rsi < self.rsi_oversold:
            return Signal.BUY

        if prev_close >= prev_upper and curr_close < curr_upper and curr_rsi > self.rsi_overbought:
            return Signal.SELL

        return Signal.HOLD

    def calculate_sl_tp(self, signal: Signal, data: pd.DataFrame) -> SLTPLevels:
        close = data["close"]
        upper, middle, lower = self.bollinger_bands(close, self.bb_period, self.bb_deviation)
        atr_val = self.atr(data, self.atr_period)

        current_atr = atr_val.iloc[-1]
        curr_close = close.iloc[-1]
        curr_middle = middle.iloc[-1]
        curr_upper = upper.iloc[-1]
        curr_lower = lower.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            current_atr = curr_close * 0.002

        sl = current_atr * self.sl_atr_mult

        if signal == Signal.BUY:
            tp = abs(curr_middle - curr_close)
        else:
            tp = abs(curr_close - curr_middle)

        if tp <= 0:
            tp = current_atr * 2.0

        return SLTPLevels(stop_loss=sl, take_profit=tp)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timeframe": self.timeframe,
            "bb_period": self.bb_period,
            "bb_deviation": self.bb_deviation,
            "rsi_period": self.rsi_period,
            "rsi_overbought": self.rsi_overbought,
            "rsi_oversold": self.rsi_oversold,
            "sl_bb_mult": self.sl_bb_mult,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        if len(data) < max(self.bb_period, self.rsi_period) + 10:
            return False

        close = data["close"]
        upper, middle, lower = self.bollinger_bands(close, self.bb_period, self.bb_deviation)

        if np.isnan(upper.iloc[-1]) or np.isnan(lower.iloc[-1]):
            return False

        band_width = (upper.iloc[-1] - lower.iloc[-1]) / middle.iloc[-1]
        if band_width < 0.001:
            return False

        adx_val = self.adx(data, 14)
        if not np.isnan(adx_val.iloc[-1]) and adx_val.iloc[-1] > 40:
            return False

        return True

    def _get_min_bars(self) -> int:
        return max(self.bb_period, self.rsi_period, self.atr_period) + 10
