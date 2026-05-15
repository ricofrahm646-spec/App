"""Session-based breakout trading strategy."""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal, Direction

logger = logging.getLogger(__name__)

SESSION_TIMES_UTC = {
    "asian":    {"start": 0, "end": 8},
    "london":   {"start": 7, "end": 16},
    "new_york": {"start": 12, "end": 21},
}


class SessionStrategy(BaseStrategy):
    """Trades session opens by breaking out of the prior session's range."""

    @property
    def name(self) -> str:
        return "Session Strategy"

    @property
    def description(self) -> str:
        return (
            f"Breakout of {self._parameters['range_session'].title()} session range "
            f"during {self._parameters['target_session'].title()} session"
        )

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "target_session": "london",
            "range_session": "asian",
            "atr_period": 14,
            "sl_atr_mult": 1.0,
            "tp_atr_mult": 2.0,
            "breakout_buffer_pips": 2.0,
            "pip_size": 0.0001,
        }

    @staticmethod
    def _in_session(hour: int, session_name: str) -> bool:
        s = SESSION_TIMES_UTC.get(session_name)
        if not s:
            return False
        if s["start"] <= s["end"]:
            return s["start"] <= hour < s["end"]
        return hour >= s["start"] or hour < s["end"]

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters

        if len(data) < p["atr_period"] + 50:
            return Signal(direction=Direction.NONE, confidence=0.0)

        if "time" not in data.columns and not hasattr(data.index, "hour"):
            return Signal(direction=Direction.NONE, confidence=0.0)

        times = data.index if hasattr(data.index, "hour") else pd.to_datetime(data["time"])
        if len(times) == 0:
            return Signal(direction=Direction.NONE, confidence=0.0)

        current_hour = times[-1].hour if hasattr(times[-1], "hour") else 0
        if not self._in_session(current_hour, p["target_session"]):
            return Signal(direction=Direction.NONE, confidence=0.0)

        range_mask = np.array([
            self._in_session(t.hour if hasattr(t, "hour") else 0, p["range_session"])
            for t in times
        ])

        if not range_mask.any():
            return Signal(direction=Direction.NONE, confidence=0.0)

        range_data = data.iloc[range_mask]
        if len(range_data) < 2:
            return Signal(direction=Direction.NONE, confidence=0.0)

        range_high = range_data["high"].max()
        range_low = range_data["low"].min()
        buffer = p["breakout_buffer_pips"] * p["pip_size"]

        close = data["close"]
        high = data["high"]
        low = data["low"]

        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(p["atr_period"]).mean().iloc[-1]

        if np.isnan(atr) or atr <= 0:
            return Signal(direction=Direction.NONE, confidence=0.0)

        cur_close = close.iloc[-1]
        prev_close = close.iloc[-2]

        if cur_close > range_high + buffer and prev_close <= range_high + buffer:
            sl = cur_close - atr * p["sl_atr_mult"]
            tp = cur_close + atr * p["tp_atr_mult"]
            conf = min(0.85, 0.5 + (cur_close - range_high) / atr * 0.2)
            return Signal(
                direction=Direction.BUY,
                confidence=round(conf, 3),
                entry_price=cur_close,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        if cur_close < range_low - buffer and prev_close >= range_low - buffer:
            sl = cur_close + atr * p["sl_atr_mult"]
            tp = cur_close - atr * p["tp_atr_mult"]
            conf = min(0.85, 0.5 + (range_low - cur_close) / atr * 0.2)
            return Signal(
                direction=Direction.SELL,
                confidence=round(conf, 3),
                entry_price=cur_close,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        return Signal(direction=Direction.NONE, confidence=0.0)
