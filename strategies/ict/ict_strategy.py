"""ICT (Inner Circle Trader) strategy implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Direction, Signal


@dataclass
class OrderBlock:
    index: int
    high: float
    low: float
    direction: Direction
    volume: float = 0.0


@dataclass
class FairValueGap:
    index: int
    upper: float
    lower: float
    direction: Direction


@dataclass
class LiquiditySweep:
    index: int
    level: float
    direction: Direction


_KILL_ZONES: Dict[str, Tuple[int, int]] = {
    "london_open": (2, 5),   # 02:00 – 05:00 UTC (NY time 9pm–12am)
    "ny_open": (12, 15),     # 12:00 – 15:00 UTC (NY time 7am–10am)
}


class ICTStrategy(BaseStrategy):
    """ICT-style strategy: order blocks, FVG, liquidity sweeps, OTE."""

    @property
    def name(self) -> str:
        return "ICT Strategy"

    @property
    def description(self) -> str:
        return (
            "Inner Circle Trader methodology combining order block detection, "
            "fair value gaps, liquidity sweeps, and optimal trade entry via "
            "Fibonacci retracements. Active only during kill zones."
        )

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "ob_lookback": 20,
            "fvg_min_gap_pips": 5,
            "swing_lookback": 50,
            "ote_fib_low": 0.618,
            "ote_fib_high": 0.786,
            "sl_buffer_pips": 10,
            "tp_rr": 3.0,
            "pip_value": 0.0001,
            "htf_ema_period": 200,
            "kill_zone_filter": True,
            "min_confidence": 0.5,
        }

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        if len(data) < max(p["ob_lookback"], p["swing_lookback"], p["htf_ema_period"]) + 5:
            return Signal(direction=Direction.NONE, confidence=0.0)

        if p["kill_zone_filter"] and not self._in_kill_zone(data.index[-1]):
            return Signal(direction=Direction.NONE, confidence=0.0)

        bias = self._htf_bias(data, p["htf_ema_period"])
        order_blocks = self._detect_order_blocks(data, p["ob_lookback"])
        fvgs = self._detect_fvg(data, p["fvg_min_gap_pips"] * p["pip_value"])
        sweeps = self._detect_liquidity_sweeps(data, p["swing_lookback"])

        price = data["close"].iloc[-1]
        pip = p["pip_value"]

        score = 0.0
        direction = Direction.NONE

        if bias == Direction.BUY:
            bullish_obs = [ob for ob in order_blocks if ob.direction == Direction.BUY]
            bullish_fvgs = [f for f in fvgs if f.direction == Direction.BUY]
            buy_sweeps = [s for s in sweeps if s.direction == Direction.BUY]

            in_ob = any(ob.low <= price <= ob.high for ob in bullish_obs)
            in_fvg = any(f.lower <= price <= f.upper for f in bullish_fvgs)
            sweep_present = len(buy_sweeps) > 0

            if in_ob:
                score += 0.35
            if in_fvg:
                score += 0.30
            if sweep_present:
                score += 0.20

            ote_zone = self._ote_zone(data, Direction.BUY, p["swing_lookback"])
            if ote_zone and ote_zone[0] <= price <= ote_zone[1]:
                score += 0.15

            if score >= p["min_confidence"]:
                direction = Direction.BUY

        elif bias == Direction.SELL:
            bearish_obs = [ob for ob in order_blocks if ob.direction == Direction.SELL]
            bearish_fvgs = [f for f in fvgs if f.direction == Direction.SELL]
            sell_sweeps = [s for s in sweeps if s.direction == Direction.SELL]

            in_ob = any(ob.low <= price <= ob.high for ob in bearish_obs)
            in_fvg = any(f.lower <= price <= f.upper for f in bearish_fvgs)
            sweep_present = len(sell_sweeps) > 0

            if in_ob:
                score += 0.35
            if in_fvg:
                score += 0.30
            if sweep_present:
                score += 0.20

            ote_zone = self._ote_zone(data, Direction.SELL, p["swing_lookback"])
            if ote_zone and ote_zone[0] <= price <= ote_zone[1]:
                score += 0.15

            if score >= p["min_confidence"]:
                direction = Direction.SELL

        if direction == Direction.NONE:
            return Signal(direction=Direction.NONE, confidence=0.0)

        confidence = min(score, 1.0)
        sl_dist = p["sl_buffer_pips"] * pip
        tp_dist = sl_dist * p["tp_rr"]

        if direction == Direction.BUY:
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            sl = price + sl_dist
            tp = price - tp_dist

        return Signal(
            direction=direction,
            confidence=confidence,
            entry_price=price,
            sl=sl,
            tp=tp,
        )

    # ------------------------------------------------------------------
    # ICT components
    # ------------------------------------------------------------------

    @staticmethod
    def _htf_bias(data: pd.DataFrame, period: int) -> Direction:
        ema = data["close"].ewm(span=period, adjust=False).mean()
        if data["close"].iloc[-1] > ema.iloc[-1]:
            return Direction.BUY
        elif data["close"].iloc[-1] < ema.iloc[-1]:
            return Direction.SELL
        return Direction.NONE

    @staticmethod
    def _detect_order_blocks(
        data: pd.DataFrame, lookback: int
    ) -> List[OrderBlock]:
        blocks: List[OrderBlock] = []
        subset = data.iloc[-lookback:]
        closes = subset["close"].values
        opens = subset["open"].values
        highs = subset["high"].values
        lows = subset["low"].values
        volumes = subset["volume"].values if "volume" in subset.columns else np.ones(len(subset))

        for i in range(1, len(subset) - 1):
            body_prev = closes[i - 1] - opens[i - 1]
            body_curr = closes[i] - opens[i]

            if body_prev < 0 and body_curr > 0 and abs(body_curr) > abs(body_prev):
                blocks.append(
                    OrderBlock(
                        index=i,
                        high=highs[i - 1],
                        low=lows[i - 1],
                        direction=Direction.BUY,
                        volume=float(volumes[i - 1]),
                    )
                )
            elif body_prev > 0 and body_curr < 0 and abs(body_curr) > abs(body_prev):
                blocks.append(
                    OrderBlock(
                        index=i,
                        high=highs[i - 1],
                        low=lows[i - 1],
                        direction=Direction.SELL,
                        volume=float(volumes[i - 1]),
                    )
                )
        return blocks

    @staticmethod
    def _detect_fvg(data: pd.DataFrame, min_gap: float) -> List[FairValueGap]:
        gaps: List[FairValueGap] = []
        if len(data) < 3:
            return gaps

        highs = data["high"].values
        lows = data["low"].values

        for i in range(2, len(data)):
            if lows[i] > highs[i - 2] and (lows[i] - highs[i - 2]) >= min_gap:
                gaps.append(
                    FairValueGap(
                        index=i,
                        upper=float(lows[i]),
                        lower=float(highs[i - 2]),
                        direction=Direction.BUY,
                    )
                )
            elif highs[i] < lows[i - 2] and (lows[i - 2] - highs[i]) >= min_gap:
                gaps.append(
                    FairValueGap(
                        index=i,
                        upper=float(lows[i - 2]),
                        lower=float(highs[i]),
                        direction=Direction.SELL,
                    )
                )
        return gaps

    @staticmethod
    def _detect_liquidity_sweeps(
        data: pd.DataFrame, lookback: int
    ) -> List[LiquiditySweep]:
        sweeps: List[LiquiditySweep] = []
        if len(data) < lookback + 2:
            return sweeps

        recent = data.iloc[-lookback:]
        prev = data.iloc[-(lookback + 2) : -2]

        prev_high = prev["high"].max()
        prev_low = prev["low"].min()
        last_high = recent["high"].iloc[-1]
        last_low = recent["low"].iloc[-1]
        last_close = recent["close"].iloc[-1]

        if last_high > prev_high and last_close < prev_high:
            sweeps.append(
                LiquiditySweep(
                    index=len(data) - 1,
                    level=float(prev_high),
                    direction=Direction.BUY,
                )
            )
        if last_low < prev_low and last_close > prev_low:
            sweeps.append(
                LiquiditySweep(
                    index=len(data) - 1,
                    level=float(prev_low),
                    direction=Direction.SELL,
                )
            )

        # A sweep of lows followed by reversal → bullish entry
        # A sweep of highs followed by reversal → bearish entry
        # (directions above denote the *entry* direction after the sweep)
        return sweeps

    @staticmethod
    def _ote_zone(
        data: pd.DataFrame, direction: Direction, lookback: int
    ) -> Optional[Tuple[float, float]]:
        """Return the Optimal Trade Entry (Fibonacci 0.618–0.786) zone."""
        subset = data.iloc[-lookback:]
        swing_high = float(subset["high"].max())
        swing_low = float(subset["low"].min())
        swing_range = swing_high - swing_low
        if swing_range == 0:
            return None

        if direction == Direction.BUY:
            upper = swing_high - 0.618 * swing_range
            lower = swing_high - 0.786 * swing_range
            return (lower, upper)
        else:
            lower = swing_low + 0.618 * swing_range
            upper = swing_low + 0.786 * swing_range
            return (lower, upper)

    @staticmethod
    def _in_kill_zone(timestamp: pd.Timestamp) -> bool:
        if not hasattr(timestamp, "hour"):
            return True
        h = timestamp.hour
        for start, end in _KILL_ZONES.values():
            if start <= h < end:
                return True
        return False
