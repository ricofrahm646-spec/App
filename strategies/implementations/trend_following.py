"""
Trend Following Strategy: ADX + Moving Average + ATR.

Medium-to-long term strategy that identifies and rides strong trends using
ADX for trend strength, directional indicators for direction, MA for
confirmation, and ATR for dynamic SL/TP.
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


class TrendFollowingStrategy(BaseStrategy):
    """Trend following strategy using ADX, DI crossover, and MA filter.

    Entry logic:
        - BUY: ADX > threshold (strong trend), +DI crosses above -DI,
          price above moving average.
        - SELL: ADX > threshold, -DI crosses above +DI, price below MA.

    Exit: ATR-based dynamic SL/TP.
    """

    def __init__(
        self,
        name: str = "TrendFollowing_ADX_MA",
        timeframe: str = "H1",
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        ma_period: int = 50,
        ma_type: str = "ema",
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 3.0,
    ) -> None:
        super().__init__(name, timeframe)
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.ma_period = ma_period
        self.ma_type = ma_type
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < max(self.adx_period, self.ma_period) + 5:
            return Signal.HOLD

        close = data["close"]
        high = data["high"]
        low = data["low"]

        adx_val = self.adx(data, self.adx_period)
        plus_di, minus_di = self._directional_indicators(data, self.adx_period)

        if self.ma_type == "ema":
            ma_val = self.ema(close, self.ma_period)
        else:
            ma_val = self.sma(close, self.ma_period)

        curr_adx = adx_val.iloc[-1]
        curr_plus_di = plus_di.iloc[-1]
        prev_plus_di = plus_di.iloc[-2]
        curr_minus_di = minus_di.iloc[-1]
        prev_minus_di = minus_di.iloc[-2]
        curr_close = close.iloc[-1]
        curr_ma = ma_val.iloc[-1]

        if np.isnan(curr_adx) or np.isnan(curr_plus_di) or np.isnan(curr_ma):
            return Signal.HOLD

        strong_trend = curr_adx > self.adx_threshold

        if (strong_trend and
                curr_plus_di > curr_minus_di and
                prev_plus_di <= prev_minus_di and
                curr_close > curr_ma):
            return Signal.BUY

        if (strong_trend and
                curr_minus_di > curr_plus_di and
                prev_minus_di <= prev_plus_di and
                curr_close < curr_ma):
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
            "adx_period": self.adx_period,
            "adx_threshold": self.adx_threshold,
            "ma_period": self.ma_period,
            "ma_type": self.ma_type,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
            "tp_atr_mult": self.tp_atr_mult,
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        if len(data) < max(self.adx_period, self.ma_period) + 10:
            return False

        atr_val = self.atr(data, self.atr_period)
        if np.isnan(atr_val.iloc[-1]):
            return False

        adx_val = self.adx(data, self.adx_period)
        if np.isnan(adx_val.iloc[-1]):
            return False

        return True

    @staticmethod
    def _directional_indicators(
        data: pd.DataFrame, period: int
    ) -> tuple[pd.Series, pd.Series]:
        """Calculate +DI and -DI directional indicators."""
        high = data["high"]
        low = data["low"]
        close = data["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr_val = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        safe_atr = atr_val.replace(0, np.finfo(float).eps)

        plus_di = 100 * plus_dm.ewm(
            alpha=1.0 / period, min_periods=period, adjust=False
        ).mean() / safe_atr
        minus_di = 100 * minus_dm.ewm(
            alpha=1.0 / period, min_periods=period, adjust=False
        ).mean() / safe_atr

        return plus_di, minus_di

    def _get_min_bars(self) -> int:
        return max(self.adx_period, self.ma_period, self.atr_period) + 10
