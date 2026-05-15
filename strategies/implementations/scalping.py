"""
Scalping Strategy: EMA Crossover + RSI + Volume.

Short-term strategy targeting small, frequent gains using fast EMA crossovers
confirmed by RSI momentum and above-average volume.
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


class ScalpingStrategy(BaseStrategy):
    """Scalping strategy using EMA crossover, RSI filter, and volume confirmation.

    Entry logic:
        - BUY: Fast EMA crosses above Slow EMA, RSI between oversold and overbought,
          volume above average * multiplier.
        - SELL: Fast EMA crosses below Slow EMA, same RSI and volume conditions.

    Exit: Fixed SL/TP based on ATR multiples.
    """

    def __init__(
        self,
        name: str = "Scalping_EMA_RSI",
        timeframe: str = "M5",
        ema_fast: int = 8,
        ema_slow: int = 21,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        volume_multiplier: float = 1.5,
        atr_period: int = 14,
        sl_atr_mult: float = 1.0,
        tp_atr_mult: float = 1.5,
    ) -> None:
        super().__init__(name, timeframe)
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.volume_multiplier = volume_multiplier
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.ema_slow + 2:
            return Signal.HOLD

        close = data["close"]
        ema_f = self.ema(close, self.ema_fast)
        ema_s = self.ema(close, self.ema_slow)
        rsi_val = self.rsi(close, self.rsi_period)

        vol = data["volume"]
        avg_vol = vol.rolling(window=20).mean()

        curr_ema_f = ema_f.iloc[-1]
        prev_ema_f = ema_f.iloc[-2]
        curr_ema_s = ema_s.iloc[-1]
        prev_ema_s = ema_s.iloc[-2]
        curr_rsi = rsi_val.iloc[-1]
        curr_vol = vol.iloc[-1]
        curr_avg_vol = avg_vol.iloc[-1]

        if np.isnan(curr_rsi) or np.isnan(curr_avg_vol):
            return Signal.HOLD

        high_volume = curr_vol > curr_avg_vol * self.volume_multiplier

        if (prev_ema_f <= prev_ema_s and curr_ema_f > curr_ema_s and
                self.rsi_oversold < curr_rsi < self.rsi_overbought and high_volume):
            return Signal.BUY

        if (prev_ema_f >= prev_ema_s and curr_ema_f < curr_ema_s and
                self.rsi_oversold < curr_rsi < self.rsi_overbought and high_volume):
            return Signal.SELL

        return Signal.HOLD

    def calculate_sl_tp(self, signal: Signal, data: pd.DataFrame) -> SLTPLevels:
        atr_val = self.atr(data, self.atr_period)
        current_atr = atr_val.iloc[-1]

        if np.isnan(current_atr) or current_atr <= 0:
            current_atr = data["close"].iloc[-1] * 0.001

        sl = current_atr * self.sl_atr_mult
        tp = current_atr * self.tp_atr_mult

        return SLTPLevels(stop_loss=sl, take_profit=tp)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timeframe": self.timeframe,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "rsi_period": self.rsi_period,
            "rsi_overbought": self.rsi_overbought,
            "rsi_oversold": self.rsi_oversold,
            "volume_multiplier": self.volume_multiplier,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
            "tp_atr_mult": self.tp_atr_mult,
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        if len(data) < self.ema_slow + 10:
            return False

        close = data["close"]
        atr_val = self.atr(data, self.atr_period)

        if atr_val.iloc[-1] is None or np.isnan(atr_val.iloc[-1]):
            return False

        recent_spread = (data["high"].iloc[-1] - data["low"].iloc[-1])
        avg_atr = atr_val.iloc[-20:].mean()

        if recent_spread > avg_atr * 3:
            return False

        return True

    def _get_min_bars(self) -> int:
        return max(self.ema_slow, self.rsi_period, 20) + 5
