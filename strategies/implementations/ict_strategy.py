"""
ICT / Smart Money Concepts Strategy.

Implements institutional trading concepts: Order Blocks, Liquidity Sweeps,
Fair Value Gaps (FVG), and session-based killzone timing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from strategies.implementations.base_strategy import (
    BaseStrategy,
    Signal,
    SLTPLevels,
)


class ICTStrategy(BaseStrategy):
    """ICT/Smart Money strategy based on order blocks, liquidity sweeps, and FVG.

    Entry logic:
        - Detect Order Blocks (last opposing candle before an impulsive move).
        - Detect Fair Value Gaps (imbalance between candle wicks).
        - Detect Liquidity Sweeps (price sweeps a swing then reverses).
        - Trade only during London/NY killzones.
        - BUY when price retraces into a bullish OB with FVG or sweep confirmation.
        - SELL when price retraces into a bearish OB with FVG or sweep confirmation.
    """

    def __init__(
        self,
        name: str = "ICT_SmartMoney",
        timeframe: str = "M15",
        lookback: int = 50,
        ob_strength: float = 1.5,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 3.0,
        london_start: int = 7,
        london_end: int = 10,
        ny_start: int = 13,
        ny_end: int = 16,
        require_killzone: bool = True,
        fvg_min_gap_atr: float = 0.5,
    ) -> None:
        super().__init__(name, timeframe)
        self.lookback = lookback
        self.ob_strength = ob_strength
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.london_start = london_start
        self.london_end = london_end
        self.ny_start = ny_start
        self.ny_end = ny_end
        self.require_killzone = require_killzone
        self.fvg_min_gap_atr = fvg_min_gap_atr

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.lookback + 5:
            return Signal.HOLD

        opens = data["open"].values
        highs = data["high"].values
        lows = data["low"].values
        closes = data["close"].values

        if self.require_killzone and hasattr(data.index, 'hour'):
            current_hour = data.index[-1].hour
            if not self._in_killzone(current_hour):
                return Signal.HOLD

        atr_series = self.atr(data, self.atr_period)
        current_atr = atr_series.iloc[-1]
        if np.isnan(current_atr):
            return Signal.HOLD

        bull_ob = self._find_bullish_order_block(opens, highs, lows, closes)
        bear_ob = self._find_bearish_order_block(opens, highs, lows, closes)

        bull_fvg = self._detect_bullish_fvg(highs, lows, current_atr)
        bear_fvg = self._detect_bearish_fvg(highs, lows, current_atr)

        bull_sweep = self._detect_bullish_liquidity_sweep(opens, highs, lows, closes)
        bear_sweep = self._detect_bearish_liquidity_sweep(opens, highs, lows, closes)

        current_close = closes[-1]

        if bull_ob is not None:
            ob_high, ob_low = bull_ob
            if ob_low <= current_close <= ob_high:
                if bull_fvg or bull_sweep:
                    return Signal.BUY

        if bear_ob is not None:
            ob_high, ob_low = bear_ob
            if ob_low <= current_close <= ob_high:
                if bear_fvg or bear_sweep:
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
            "lookback": self.lookback,
            "ob_strength": self.ob_strength,
            "atr_period": self.atr_period,
            "sl_atr_mult": self.sl_atr_mult,
            "tp_atr_mult": self.tp_atr_mult,
            "london_start": self.london_start,
            "london_end": self.london_end,
            "ny_start": self.ny_start,
            "ny_end": self.ny_end,
            "require_killzone": self.require_killzone,
            "fvg_min_gap_atr": self.fvg_min_gap_atr,
        }

    def validate_conditions(self, data: pd.DataFrame) -> bool:
        if len(data) < self.lookback + 5:
            return False

        atr_series = self.atr(data, self.atr_period)
        if atr_series.iloc[-1] is None or np.isnan(atr_series.iloc[-1]):
            return False

        recent_atr = atr_series.iloc[-5:].mean()
        historical_atr = atr_series.iloc[-30:-5].mean()

        if not np.isnan(historical_atr) and historical_atr > 0:
            if recent_atr < historical_atr * 0.3:
                return False

        return True

    def _in_killzone(self, hour: int) -> bool:
        """Check if the current hour falls within a killzone session."""
        in_london = self.london_start <= hour < self.london_end
        in_ny = self.ny_start <= hour < self.ny_end
        return in_london or in_ny

    def _find_bullish_order_block(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> Optional[Tuple[float, float]]:
        """Find the most recent bullish order block.

        A bullish OB is a bearish candle immediately followed by an impulsive
        bullish candle whose body exceeds the bearish body by ob_strength.
        """
        n = len(closes)
        search_end = max(n - self.lookback, 2)

        for i in range(n - 2, search_end, -1):
            is_bearish = closes[i] < opens[i]
            is_next_bullish = closes[i + 1] > opens[i + 1]

            if is_bearish and is_next_bullish:
                bear_body = opens[i] - closes[i]
                bull_body = closes[i + 1] - opens[i + 1]

                if bear_body > 0 and bull_body > bear_body * self.ob_strength:
                    return (highs[i], lows[i])

        return None

    def _find_bearish_order_block(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> Optional[Tuple[float, float]]:
        """Find the most recent bearish order block."""
        n = len(closes)
        search_end = max(n - self.lookback, 2)

        for i in range(n - 2, search_end, -1):
            is_bullish = closes[i] > opens[i]
            is_next_bearish = closes[i + 1] < opens[i + 1]

            if is_bullish and is_next_bearish:
                bull_body = closes[i] - opens[i]
                bear_body = opens[i + 1] - closes[i + 1]

                if bull_body > 0 and bear_body > bull_body * self.ob_strength:
                    return (highs[i], lows[i])

        return None

    def _detect_bullish_fvg(
        self, highs: np.ndarray, lows: np.ndarray, current_atr: float
    ) -> bool:
        """Detect a bullish Fair Value Gap in the last few bars.

        Bullish FVG: gap between candle N-2 high and candle N low (price skipped up).
        """
        if len(highs) < 4:
            return False

        for offset in range(1, min(4, len(highs) - 2)):
            gap = lows[-offset] - highs[-offset - 2]
            if gap > current_atr * self.fvg_min_gap_atr:
                return True

        return False

    def _detect_bearish_fvg(
        self, highs: np.ndarray, lows: np.ndarray, current_atr: float
    ) -> bool:
        """Detect a bearish Fair Value Gap in the last few bars."""
        if len(lows) < 4:
            return False

        for offset in range(1, min(4, len(lows) - 2)):
            gap = lows[-offset - 2] - highs[-offset]
            if gap > current_atr * self.fvg_min_gap_atr:
                return True

        return False

    def _detect_bullish_liquidity_sweep(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> bool:
        """Detect a bullish liquidity sweep: price swept a recent low then reversed up."""
        if len(lows) < self.lookback:
            return False

        search_start = max(len(lows) - self.lookback, 0)
        recent_low = np.min(lows[search_start:-2])

        swept = lows[-2] < recent_low
        reversed_up = closes[-1] > opens[-1]

        return swept and reversed_up

    def _detect_bearish_liquidity_sweep(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> bool:
        """Detect a bearish liquidity sweep: price swept a recent high then reversed down."""
        if len(highs) < self.lookback:
            return False

        search_start = max(len(highs) - self.lookback, 0)
        recent_high = np.max(highs[search_start:-2])

        swept = highs[-2] > recent_high
        reversed_down = closes[-1] < opens[-1]

        return swept and reversed_down

    def _get_min_bars(self) -> int:
        return max(self.lookback + 5, self.atr_period + 5)
