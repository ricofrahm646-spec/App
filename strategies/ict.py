"""
JARVIS ICT (Inner Circle Trader) Strategy
Implements: Order Blocks, Fair Value Gaps, Liquidity Sweeps, Market Structure Shifts.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .base import BaseStrategy, Signal, StrategyConfig


@dataclass
class OrderBlock:
    index: int
    high: float
    low: float
    direction: str   # BULLISH or BEARISH
    mitigated: bool = False
    strength: float = 1.0


@dataclass
class FairValueGap:
    index: int
    top: float
    bottom: float
    direction: str   # BULLISH or BEARISH
    filled: bool = False


class ICTStrategy(BaseStrategy):
    """
    ICT-based strategy:
    - Identifies Swing Highs/Lows for market structure
    - Detects Order Blocks (last opposing candle before impulse)
    - Detects Fair Value Gaps (3-candle FVG)
    - Detects Liquidity Sweeps (stop hunts above/below swing points)
    - Enters on retest of order block during kill zones
    - Uses ATR for adaptive SL
    """

    name = "ICT_Master"
    version = "1.5.0"
    strategy_type = "ICT"
    description = "ICT strategy: Order Blocks, FVGs, Liquidity Sweeps, Kill Zone entries"

    KILL_ZONES = {
        "LONDON_OPEN": (8, 10),
        "NEWYORK_OPEN": (13, 15),
        "LONDON_CLOSE": (15, 17),
    }

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        super().__init__(config)
        self.swing_lookback = 5
        self.ob_lookback = 20
        self.atr_period = 14
        self.atr_sl_mult = 1.0

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["atr"] = self._atr(df["high"], df["low"], df["close"], self.atr_period)
        df["swing_high"] = df["high"].rolling(self.swing_lookback * 2 + 1, center=True).max() == df["high"]
        df["swing_low"] = df["low"].rolling(self.swing_lookback * 2 + 1, center=True).min() == df["low"]
        df["body"] = (df["close"] - df["open"]).abs()
        df["is_bull"] = df["close"] > df["open"]
        df["is_bear"] = df["close"] < df["open"]
        return df

    def detect_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """Detect bullish and bearish order blocks."""
        obs: List[OrderBlock] = []
        lookback = min(self.ob_lookback, len(df) - 3)

        for i in range(1, lookback):
            idx = -(lookback - i + 1)
            candle = df.iloc[idx]
            next_candle = df.iloc[idx + 1]

            # Bullish OB: last bearish candle before a bullish impulse
            if candle["is_bear"] and next_candle["is_bull"]:
                if next_candle["close"] > candle["high"]:
                    obs.append(OrderBlock(
                        index=idx,
                        high=float(candle["high"]),
                        low=float(candle["low"]),
                        direction="BULLISH",
                        strength=float(next_candle["body"] / (candle["body"] + 1e-10)),
                    ))

            # Bearish OB: last bullish candle before a bearish impulse
            if candle["is_bull"] and next_candle["is_bear"]:
                if next_candle["close"] < candle["low"]:
                    obs.append(OrderBlock(
                        index=idx,
                        high=float(candle["high"]),
                        low=float(candle["low"]),
                        direction="BEARISH",
                        strength=float(next_candle["body"] / (candle["body"] + 1e-10)),
                    ))

        return obs

    def detect_fvg(self, df: pd.DataFrame) -> List[FairValueGap]:
        """Detect Fair Value Gaps (3-candle pattern)."""
        fvgs: List[FairValueGap] = []
        lookback = min(self.ob_lookback, len(df) - 3)

        for i in range(1, lookback):
            idx = -(lookback - i + 1)
            c1 = df.iloc[idx - 1]
            c3 = df.iloc[idx + 1]

            # Bullish FVG: c1.high < c3.low
            if c1["high"] < c3["low"]:
                fvgs.append(FairValueGap(
                    index=idx,
                    top=float(c3["low"]),
                    bottom=float(c1["high"]),
                    direction="BULLISH",
                ))

            # Bearish FVG: c1.low > c3.high
            if c1["low"] > c3["high"]:
                fvgs.append(FairValueGap(
                    index=idx,
                    top=float(c1["low"]),
                    bottom=float(c3["high"]),
                    direction="BEARISH",
                ))

        return fvgs

    def is_kill_zone(self, timestamp: pd.Timestamp) -> Tuple[bool, str]:
        """Check if current time is within an ICT kill zone."""
        hour = timestamp.hour
        for name, (start, end) in self.KILL_ZONES.items():
            if start <= hour < end:
                return True, name
        return False, ""

    def detect_liquidity_sweep(self, df: pd.DataFrame) -> Optional[str]:
        """Detect if the last candle swept a swing high/low."""
        recent = df.tail(10)
        swing_highs = recent[recent["swing_high"]]["high"]
        swing_lows = recent[recent["swing_low"]]["low"]
        last = df.iloc[-1]

        # Sweep above swing high then close back below
        if len(swing_highs) > 0:
            nearest_high = swing_highs.max()
            if last["high"] > nearest_high and last["close"] < nearest_high:
                return "SWEEP_HIGH"

        # Sweep below swing low then close back above
        if len(swing_lows) > 0:
            nearest_low = swing_lows.min()
            if last["low"] < nearest_low and last["close"] > nearest_low:
                return "SWEEP_LOW"

        return None

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if len(data) < 50:
            return None

        df = self.calculate_indicators(data)
        last = df.iloc[-1]
        timestamp = df.index[-1]

        in_kill_zone, zone_name = self.is_kill_zone(timestamp)
        if not in_kill_zone:
            return None

        atr = float(last["atr"])
        if atr == 0:
            return None

        current_price = float(last["close"])
        order_blocks = self.detect_order_blocks(df)
        sweep = self.detect_liquidity_sweep(df)
        fvgs = self.detect_fvg(df)

        # BUY: bullish OB retest after sweep of lows during kill zone
        if sweep == "SWEEP_LOW":
            bullish_obs = [ob for ob in order_blocks if ob.direction == "BULLISH" and ob.strength > 1.0]
            if bullish_obs:
                nearest_ob = min(bullish_obs, key=lambda x: abs(current_price - (x.high + x.low) / 2))
                ob_mid = (nearest_ob.high + nearest_ob.low) / 2
                if nearest_ob.low <= current_price <= nearest_ob.high * 1.001:
                    return Signal(
                        action="BUY",
                        symbol=self.config.symbol,
                        entry_price=current_price,
                        stop_loss=round(nearest_ob.low - atr * self.atr_sl_mult, 5),
                        take_profit=round(current_price + (current_price - nearest_ob.low) * 2.5, 5),
                        confidence=min(0.85, 0.6 + nearest_ob.strength * 0.1),
                        reasoning=f"Bullish OB retest after liquidity sweep ({zone_name})",
                        timeframe=self.config.timeframe,
                    )

        # SELL: bearish OB retest after sweep of highs during kill zone
        if sweep == "SWEEP_HIGH":
            bearish_obs = [ob for ob in order_blocks if ob.direction == "BEARISH" and ob.strength > 1.0]
            if bearish_obs:
                nearest_ob = min(bearish_obs, key=lambda x: abs(current_price - (x.high + x.low) / 2))
                if nearest_ob.low <= current_price <= nearest_ob.high * 1.001:
                    return Signal(
                        action="SELL",
                        symbol=self.config.symbol,
                        entry_price=current_price,
                        stop_loss=round(nearest_ob.high + atr * self.atr_sl_mult, 5),
                        take_profit=round(current_price - (nearest_ob.high - current_price) * 2.5, 5),
                        confidence=min(0.85, 0.6 + nearest_ob.strength * 0.1),
                        reasoning=f"Bearish OB retest after liquidity sweep ({zone_name})",
                        timeframe=self.config.timeframe,
                    )

        # FVG fill entry
        bullish_fvgs = [f for f in fvgs if f.direction == "BULLISH" and not f.filled]
        bearish_fvgs = [f for f in fvgs if f.direction == "BEARISH" and not f.filled]

        for fvg in bullish_fvgs:
            if fvg.bottom <= current_price <= fvg.top:
                return Signal(
                    action="BUY",
                    symbol=self.config.symbol,
                    entry_price=current_price,
                    stop_loss=round(fvg.bottom - atr, 5),
                    take_profit=round(current_price + (fvg.top - fvg.bottom) * 3, 5),
                    confidence=0.65,
                    reasoning=f"Bullish FVG fill entry ({zone_name})",
                    timeframe=self.config.timeframe,
                )

        for fvg in bearish_fvgs:
            if fvg.bottom <= current_price <= fvg.top:
                return Signal(
                    action="SELL",
                    symbol=self.config.symbol,
                    entry_price=current_price,
                    stop_loss=round(fvg.top + atr, 5),
                    take_profit=round(current_price - (fvg.top - fvg.bottom) * 3, 5),
                    confidence=0.65,
                    reasoning=f"Bearish FVG fill entry ({zone_name})",
                    timeframe=self.config.timeframe,
                )

        return None
