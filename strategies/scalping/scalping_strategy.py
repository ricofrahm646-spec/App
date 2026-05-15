"""EMA-crossover scalping strategy with RSI filter."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Direction, Signal

# Session boundaries in UTC (hour, minute)
_SESSIONS: Dict[str, tuple] = {
    "london_open": (7, 0),
    "london_close": (16, 0),
    "ny_open": (12, 0),
    "ny_close": (21, 0),
}


class ScalpingStrategy(BaseStrategy):
    """Fast EMA / slow EMA crossover with RSI filter.

    Trades only during the London and New York sessions, targeting
    small pip moves typical of a scalping approach.
    """

    @property
    def name(self) -> str:
        return "EMA Crossover Scalper"

    @property
    def description(self) -> str:
        return (
            "Scalping strategy using fast/slow EMA crossover filtered by RSI "
            "extremes. Active only during London and New York sessions."
        )

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "fast_ema": 9,
            "slow_ema": 21,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "sl_pips": 15,
            "tp_pips": 20,
            "pip_value": 0.0001,
            "session_filter": True,
        }

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        if len(data) < p["slow_ema"] + 2:
            return Signal(direction=Direction.NONE, confidence=0.0)

        close = data["close"]
        fast = close.ewm(span=p["fast_ema"], adjust=False).mean()
        slow = close.ewm(span=p["slow_ema"], adjust=False).mean()
        rsi = self._rsi(close, p["rsi_period"])

        if rsi is None:
            return Signal(direction=Direction.NONE, confidence=0.0)

        if p["session_filter"] and not self._in_session(data.index[-1]):
            return Signal(direction=Direction.NONE, confidence=0.0)

        current_fast = fast.iloc[-1]
        prev_fast = fast.iloc[-2]
        current_slow = slow.iloc[-1]
        prev_slow = slow.iloc[-2]
        current_rsi = rsi.iloc[-1]
        price = close.iloc[-1]
        pip = p["pip_value"]

        crossover_up = prev_fast <= prev_slow and current_fast > current_slow
        crossover_down = prev_fast >= prev_slow and current_fast < current_slow

        if crossover_up and current_rsi < p["rsi_overbought"]:
            confidence = self._confidence_from_rsi(current_rsi, Direction.BUY)
            return Signal(
                direction=Direction.BUY,
                confidence=confidence,
                entry_price=price,
                sl=price - p["sl_pips"] * pip,
                tp=price + p["tp_pips"] * pip,
            )

        if crossover_down and current_rsi > p["rsi_oversold"]:
            confidence = self._confidence_from_rsi(current_rsi, Direction.SELL)
            return Signal(
                direction=Direction.SELL,
                confidence=confidence,
                entry_price=price,
                sl=price + p["sl_pips"] * pip,
                tp=price - p["tp_pips"] * pip,
            )

        return Signal(direction=Direction.NONE, confidence=0.0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series | None:
        if len(series) < period + 1:
            return None
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - 100 / (1 + rs)

    @staticmethod
    def _confidence_from_rsi(rsi_value: float, direction: Direction) -> float:
        if direction == Direction.BUY:
            return float(np.clip((50 - rsi_value) / 50 + 0.5, 0.3, 1.0))
        return float(np.clip((rsi_value - 50) / 50 + 0.5, 0.3, 1.0))

    @staticmethod
    def _in_session(timestamp: pd.Timestamp) -> bool:
        if not hasattr(timestamp, "hour"):
            return True
        h = timestamp.hour
        london = _SESSIONS["london_open"][0] <= h < _SESSIONS["london_close"][0]
        ny = _SESSIONS["ny_open"][0] <= h < _SESSIONS["ny_close"][0]
        return london or ny
