"""Breakout trading strategy using Donchian channels."""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal, Direction

logger = logging.getLogger(__name__)


class BreakoutStrategy(BaseStrategy):
    """Detects breakouts from consolidation ranges using Donchian channels."""

    @property
    def name(self) -> str:
        return "Breakout Strategy"

    @property
    def description(self) -> str:
        return "Donchian channel breakout with ATR-based SL/TP and optional volume confirmation"

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "lookback": 20,
            "atr_period": 14,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 2.5,
            "volume_confirm": True,
            "volume_mult": 1.5,
        }

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        lb = p["lookback"]

        if len(data) < lb + p["atr_period"] + 1:
            return Signal(direction=Direction.NONE, confidence=0.0)

        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        upper_channel = pd.Series(high).rolling(lb).max().values
        lower_channel = pd.Series(low).rolling(lb).min().values

        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1]),
            ),
        )
        atr = pd.Series(tr).rolling(p["atr_period"]).mean().iloc[-1]
        if np.isnan(atr) or atr <= 0:
            return Signal(direction=Direction.NONE, confidence=0.0)

        current_close = close[-1]
        prev_close = close[-2]
        prev_upper = upper_channel[-2]
        prev_lower = lower_channel[-2]

        vol_ok = True
        if p["volume_confirm"] and "volume" in data.columns:
            vol = data["volume"].values
            avg_vol = pd.Series(vol).rolling(lb).mean().iloc[-1]
            vol_ok = vol[-1] > avg_vol * p["volume_mult"]

        if current_close > prev_upper and prev_close <= prev_upper and vol_ok:
            entry = current_close
            sl = entry - atr * p["atr_sl_mult"]
            tp = entry + atr * p["atr_tp_mult"]
            conf = min(0.95, 0.5 + (current_close - prev_upper) / atr * 0.2)
            return Signal(
                direction=Direction.BUY,
                confidence=round(conf, 3),
                entry_price=entry,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        if current_close < prev_lower and prev_close >= prev_lower and vol_ok:
            entry = current_close
            sl = entry + atr * p["atr_sl_mult"]
            tp = entry - atr * p["atr_tp_mult"]
            conf = min(0.95, 0.5 + (prev_lower - current_close) / atr * 0.2)
            return Signal(
                direction=Direction.SELL,
                confidence=round(conf, 3),
                entry_price=entry,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        return Signal(direction=Direction.NONE, confidence=0.0)
