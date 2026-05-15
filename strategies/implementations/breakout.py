"""
Breakout Strategy: Range Detection + Volume Breakout.

Identifies consolidation ranges and trades breakouts confirmed by
above-average volume and ATR expansion.
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


class BreakoutStrategy(BaseStrategy):
    """Breakout strategy using range detection and volume confirmation.

    Entry logic:
        - Detect consolidation range over lookback period (high/low channel).
        - BUY when price closes above range high with volume > avg * multiplier.
        - SELL when price closes below range low with volume > avg * multiplier.
        - ATR expansion filter to avoid false breakouts during low volatility.

    Exit: SL below/above range boundary, TP at range-width projection.
    """

    def __init__(
        self,
        name: str = "Breakout_Range_Volume",
        timeframe: str = "H1",
        range_period: int = 20,
        atr_period: int = 14,
        sl_atr_mult: float = 1.0,
        tp_range_mult: float = 2.0,
        volume_multiplier: float = 1.5,
        atr_expansion_threshold: float = 1.2,
        min_range_atr: float = 2.0,
        max_range_atr: float = 10.0,
    ) -> None:
        super().__init__(name, timeframe)
        self.range_period = range_period
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_range_mult = tp_range_mult
        self.volume_multiplier = volume_multiplier
        self.atr_expansion_threshold = atr_expansion_threshold
        self.min_range_atr = min_range_atr
        self.max_range_atr = max_range_atr

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.range_period + 5:
            return Signal.HOLD

        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        range_data = data.iloc[-(self.range_period + 1):-1]
        range_high = range_data["high"].max()
        range_low = range_data["low"].min()

        atr_val = self.atr(data, self.atr_period)
        current_atr = atr_val.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            return Signal.HOLD

        range_size = range_high - range_low
        range_in_atr = range_size / current_atr

        if range_in_atr < self.min_range_atr or range_in_atr > self.max_range_atr:
            return Signal.HOLD

        avg_vol = volume.iloc[-21:-1].mean()
        curr_vol = volume.iloc[-1]
        high_volume = curr_vol > avg_vol * self.volume_multiplier

        prev_atr = atr_val.iloc[-5:-1].mean()
        atr_expanding = current_atr > prev_atr * self.atr_expansion_threshold if not np.isnan(prev_atr) else True

        curr_close = close.iloc[-1]

        if curr_close > range_high and high_volume and atr_expanding:
            return Signal.BUY

        if curr_close < range_low and high_volume and atr_expanding:
            return Signal.SELL

        return Signal.HOLD

    def calculate_sl_tp(self, signal: Signal, data: pd.DataFrame) -> SLTPLevels:
        atr_val = self.atr(data, self.atr_period)
        current_atr = atr_val.iloc[-1]

        range_data = data.iloc[-(self.range_period + 1):-1]
        range_high = range_data["high"].max()
        range_low = range_data["low"].min()
        range_size = range_high - range_low

        if np.isnan(current_atr) or current_atr <= 0:
            current_atr = data["close"].iloc[-1] * 0.002

        sl = current_atr * self.sl_atr_mult
        tp = range_size * self.tp_range_mult

        return SLTPLevels(stop_loss=sl, take_profit=tp)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timeframe": self.timeframe,
            "range_period": self.range_period,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
            "tp_range_mult": self.tp_range_mult,
            "volume_multiplier": self.volume_multiplier,
            "atr_expansion_threshold": self.atr_expansion_threshold,
            "min_range_atr": self.min_range_atr,
            "max_range_atr": self.max_range_atr,
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        if len(data) < self.range_period + 10:
            return False

        atr_val = self.atr(data, self.atr_period)
        if np.isnan(atr_val.iloc[-1]):
            return False

        if "volume" not in data.columns:
            return False

        avg_vol = data["volume"].iloc[-20:].mean()
        if avg_vol <= 0:
            return False

        return True

    def _get_min_bars(self) -> int:
        return max(self.range_period, self.atr_period, 20) + 10
