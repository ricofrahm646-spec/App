"""
Session-Based Trading Strategy: London/NY Open, Killzones.

Trades based on session timing, focusing on the high-probability windows
around London Open, New York Open, and their overlap (killzones). Uses
session-specific volatility and range analysis for entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from strategies.implementations.base_strategy import (
    BaseStrategy,
    Signal,
    SLTPLevels,
)


@dataclass
class SessionWindow:
    """Definition of a trading session window."""

    name: str
    start_hour: int
    end_hour: int
    weight: float = 1.0


DEFAULT_SESSIONS = [
    SessionWindow("Asia", 0, 7, weight=0.5),
    SessionWindow("London_Open", 7, 10, weight=1.5),
    SessionWindow("London", 10, 12, weight=1.0),
    SessionWindow("NY_Open", 13, 16, weight=1.5),
    SessionWindow("London_Close", 16, 17, weight=0.8),
    SessionWindow("NY_Afternoon", 17, 21, weight=0.6),
]


class SessionTradingStrategy(BaseStrategy):
    """Session-based trading strategy focused on London/NY killzones.

    Entry logic:
        - Only trade during defined killzone windows (London Open, NY Open).
        - Calculate the Asian session range as a baseline.
        - BUY: Price breaks above Asian high during a killzone with momentum
          confirmation (EMA alignment + RSI direction).
        - SELL: Price breaks below Asian low during a killzone with confirmation.
        - Session overlap (London/NY) gets higher weight for signal confidence.

    Exit: SL beyond session range, TP at 2-3x session range projection.
    """

    def __init__(
        self,
        name: str = "Session_LondonNY",
        timeframe: str = "M15",
        sessions: Optional[List[SessionWindow]] = None,
        asian_start: int = 0,
        asian_end: int = 7,
        london_killzone_start: int = 7,
        london_killzone_end: int = 10,
        ny_killzone_start: int = 13,
        ny_killzone_end: int = 16,
        ema_fast: int = 9,
        ema_slow: int = 21,
        rsi_period: int = 14,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_range_mult: float = 2.5,
        min_range_pips: float = 10.0,
        pip_size: float = 0.0001,
    ) -> None:
        super().__init__(name, timeframe)
        self.sessions = sessions or DEFAULT_SESSIONS
        self.asian_start = asian_start
        self.asian_end = asian_end
        self.london_killzone_start = london_killzone_start
        self.london_killzone_end = london_killzone_end
        self.ny_killzone_start = ny_killzone_start
        self.ny_killzone_end = ny_killzone_end
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_range_mult = tp_range_mult
        self.min_range_pips = min_range_pips
        self.pip_size = pip_size

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < max(self.ema_slow, self.rsi_period) + 10:
            return Signal.HOLD

        if not hasattr(data.index, "hour"):
            return Signal.HOLD

        current_hour = data.index[-1].hour

        if not self._in_killzone(current_hour):
            return Signal.HOLD

        asian_range = self._calculate_asian_range(data)
        if asian_range is None:
            return Signal.HOLD

        asian_high, asian_low = asian_range
        range_size = asian_high - asian_low

        if range_size < self.min_range_pips * self.pip_size:
            return Signal.HOLD

        close = data["close"]
        curr_close = close.iloc[-1]

        ema_f = self.ema(close, self.ema_fast)
        ema_s = self.ema(close, self.ema_slow)
        rsi_val = self.rsi(close, self.rsi_period)

        curr_ema_f = ema_f.iloc[-1]
        curr_ema_s = ema_s.iloc[-1]
        curr_rsi = rsi_val.iloc[-1]

        if np.isnan(curr_ema_f) or np.isnan(curr_ema_s) or np.isnan(curr_rsi):
            return Signal.HOLD

        bullish_bias = curr_ema_f > curr_ema_s and curr_rsi > 50
        bearish_bias = curr_ema_f < curr_ema_s and curr_rsi < 50

        if curr_close > asian_high and bullish_bias:
            return Signal.BUY

        if curr_close < asian_low and bearish_bias:
            return Signal.SELL

        return Signal.HOLD

    def calculate_sl_tp(self, signal: Signal, data: pd.DataFrame) -> SLTPLevels:
        atr_val = self.atr(data, self.atr_period)
        current_atr = atr_val.iloc[-1]

        asian_range = self._calculate_asian_range(data)

        if np.isnan(current_atr) or current_atr <= 0:
            current_atr = data["close"].iloc[-1] * 0.002

        sl = current_atr * self.sl_atr_mult

        if asian_range is not None:
            range_size = asian_range[0] - asian_range[1]
            tp = range_size * self.tp_range_mult
        else:
            tp = current_atr * 3.0

        return SLTPLevels(stop_loss=sl, take_profit=tp)

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timeframe": self.timeframe,
            "asian_start": self.asian_start,
            "asian_end": self.asian_end,
            "london_killzone_start": self.london_killzone_start,
            "london_killzone_end": self.london_killzone_end,
            "ny_killzone_start": self.ny_killzone_start,
            "ny_killzone_end": self.ny_killzone_end,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "rsi_period": self.rsi_period,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
            "tp_range_mult": self.tp_range_mult,
            "min_range_pips": self.min_range_pips,
            "pip_size": self.pip_size,
            "sessions": [(s.name, s.start_hour, s.end_hour, s.weight) for s in self.sessions],
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        if len(data) < max(self.ema_slow, self.rsi_period) + 20:
            return False

        if not hasattr(data.index, "hour"):
            return False

        atr_val = self.atr(data, self.atr_period)
        if np.isnan(atr_val.iloc[-1]):
            return False

        asian_range = self._calculate_asian_range(data)
        if asian_range is None:
            return False

        range_size = asian_range[0] - asian_range[1]
        if range_size < self.min_range_pips * self.pip_size:
            return False

        return True

    def _in_killzone(self, hour: int) -> bool:
        """Check if the current hour is within a killzone."""
        in_london = self.london_killzone_start <= hour < self.london_killzone_end
        in_ny = self.ny_killzone_start <= hour < self.ny_killzone_end
        return in_london or in_ny

    def _calculate_asian_range(self, data: pd.DataFrame) -> Optional[tuple[float, float]]:
        """Calculate the Asian session high/low range from today's data.

        Looks back through the data to find bars from the Asian session
        (asian_start to asian_end hours) and returns the high/low.
        """
        if not hasattr(data.index, "hour"):
            return None

        hours = data.index.hour
        asian_mask = (hours >= self.asian_start) & (hours < self.asian_end)

        current_date = data.index[-1].date()
        date_mask = data.index.date == current_date

        combined_mask = asian_mask & date_mask
        asian_bars = data.loc[combined_mask]

        if len(asian_bars) == 0:
            prev_date = current_date - pd.Timedelta(days=1)
            date_mask_prev = data.index.date == prev_date
            combined_mask_prev = asian_mask & date_mask_prev
            asian_bars = data.loc[combined_mask_prev]

        if len(asian_bars) < 2:
            return None

        return (float(asian_bars["high"].max()), float(asian_bars["low"].min()))

    def get_current_session(self, hour: int) -> Optional[SessionWindow]:
        """Identify which session the given hour falls into."""
        for session in self.sessions:
            if session.start_hour <= hour < session.end_hour:
                return session
        return None

    def get_session_weight(self, hour: int) -> float:
        """Get the trading weight for the current session."""
        session = self.get_current_session(hour)
        return session.weight if session else 0.0

    def _get_min_bars(self) -> int:
        return max(self.ema_slow, self.rsi_period, self.atr_period) + 20
