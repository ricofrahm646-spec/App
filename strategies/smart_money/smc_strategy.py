"""Smart Money Concepts (SMC) strategy implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Direction, Signal


@dataclass
class StructurePoint:
    """Swing high / swing low used in BOS / CHoCH detection."""

    index: int
    price: float
    is_high: bool


@dataclass
class StructureBreak:
    """Break of Structure or Change of Character event."""

    index: int
    level: float
    break_type: str  # "BOS" or "CHoCH"
    direction: Direction


@dataclass
class Zone:
    """Supply or demand zone."""

    upper: float
    lower: float
    zone_type: str  # "supply" or "demand"
    strength: float  # 0-1


@dataclass
class Imbalance:
    """Fair Value Gap / imbalance."""

    index: int
    upper: float
    lower: float
    direction: Direction


class SMCStrategy(BaseStrategy):
    """Smart Money Concepts strategy.

    Combines break-of-structure, change-of-character, supply/demand zones,
    imbalance (FVG), and liquidity-grab detection.
    """

    @property
    def name(self) -> str:
        return "Smart Money Concepts"

    @property
    def description(self) -> str:
        return (
            "SMC strategy detecting BOS, CHoCH, supply/demand zones, "
            "fair-value gaps, and liquidity grabs for institutional-style entries."
        )

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "swing_lookback": 5,
            "structure_lookback": 50,
            "zone_lookback": 30,
            "fvg_min_pips": 3,
            "sl_buffer_pips": 15,
            "tp_rr": 3.0,
            "pip_value": 0.0001,
            "min_confidence": 0.45,
            "liquidity_grab_lookback": 20,
        }

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        min_bars = max(
            p["structure_lookback"], p["zone_lookback"], p["liquidity_grab_lookback"]
        ) + p["swing_lookback"] + 5
        if len(data) < min_bars:
            return Signal(direction=Direction.NONE, confidence=0.0)

        swings = self._find_swings(data, p["swing_lookback"])
        structure = self._detect_structure_breaks(swings)
        zones = self._detect_zones(data, p["zone_lookback"])
        fvgs = self._detect_imbalances(data, p["fvg_min_pips"] * p["pip_value"])
        grabs = self._detect_liquidity_grabs(data, p["liquidity_grab_lookback"])

        price = float(data["close"].iloc[-1])
        pip = p["pip_value"]

        latest_break = structure[-1] if structure else None
        if latest_break is None:
            return Signal(direction=Direction.NONE, confidence=0.0)

        score = 0.0
        direction = latest_break.direction

        # BOS vs CHoCH weighting
        if latest_break.break_type == "BOS":
            score += 0.25
        elif latest_break.break_type == "CHoCH":
            score += 0.30

        # Zone confluence
        for z in zones:
            if direction == Direction.BUY and z.zone_type == "demand":
                if z.lower <= price <= z.upper:
                    score += 0.25 * z.strength
                    break
            elif direction == Direction.SELL and z.zone_type == "supply":
                if z.lower <= price <= z.upper:
                    score += 0.25 * z.strength
                    break

        # FVG confluence
        for fvg in fvgs:
            if fvg.direction == direction and fvg.lower <= price <= fvg.upper:
                score += 0.20
                break

        # Liquidity grab
        for grab_dir in grabs:
            if grab_dir == direction:
                score += 0.15
                break

        if score < p["min_confidence"]:
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
    # Structure analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _find_swings(data: pd.DataFrame, lookback: int) -> List[StructurePoint]:
        highs = data["high"].values
        lows = data["low"].values
        swings: List[StructurePoint] = []

        for i in range(lookback, len(data) - lookback):
            window_highs = highs[i - lookback : i + lookback + 1]
            window_lows = lows[i - lookback : i + lookback + 1]

            if highs[i] == window_highs.max():
                swings.append(StructurePoint(index=i, price=float(highs[i]), is_high=True))
            if lows[i] == window_lows.min():
                swings.append(StructurePoint(index=i, price=float(lows[i]), is_high=False))

        return swings

    @staticmethod
    def _detect_structure_breaks(
        swings: List[StructurePoint],
    ) -> List[StructureBreak]:
        breaks: List[StructureBreak] = []
        if len(swings) < 4:
            return breaks

        swing_highs = [s for s in swings if s.is_high]
        swing_lows = [s for s in swings if not s.is_high]

        # BOS: higher-high breaks previous high (bullish) or lower-low (bearish)
        for i in range(1, len(swing_highs)):
            prev, curr = swing_highs[i - 1], swing_highs[i]
            if curr.price > prev.price:
                breaks.append(
                    StructureBreak(
                        index=curr.index,
                        level=prev.price,
                        break_type="BOS",
                        direction=Direction.BUY,
                    )
                )

        for i in range(1, len(swing_lows)):
            prev, curr = swing_lows[i - 1], swing_lows[i]
            if curr.price < prev.price:
                breaks.append(
                    StructureBreak(
                        index=curr.index,
                        level=prev.price,
                        break_type="BOS",
                        direction=Direction.SELL,
                    )
                )

        # CHoCH: trend reversal – a lower-high after higher-highs, or vice-versa
        for i in range(2, len(swing_highs)):
            if (
                swing_highs[i - 2].price < swing_highs[i - 1].price
                and swing_highs[i].price < swing_highs[i - 1].price
            ):
                breaks.append(
                    StructureBreak(
                        index=swing_highs[i].index,
                        level=swing_highs[i - 1].price,
                        break_type="CHoCH",
                        direction=Direction.SELL,
                    )
                )

        for i in range(2, len(swing_lows)):
            if (
                swing_lows[i - 2].price > swing_lows[i - 1].price
                and swing_lows[i].price > swing_lows[i - 1].price
            ):
                breaks.append(
                    StructureBreak(
                        index=swing_lows[i].index,
                        level=swing_lows[i - 1].price,
                        break_type="CHoCH",
                        direction=Direction.BUY,
                    )
                )

        breaks.sort(key=lambda b: b.index)
        return breaks

    @staticmethod
    def _detect_zones(data: pd.DataFrame, lookback: int) -> List[Zone]:
        zones: List[Zone] = []
        subset = data.iloc[-lookback:]
        opens = subset["open"].values
        closes = subset["close"].values
        highs = subset["high"].values
        lows = subset["low"].values
        volumes = subset["volume"].values if "volume" in subset.columns else np.ones(len(subset))

        for i in range(1, len(subset)):
            body = abs(closes[i] - opens[i])
            full_range = highs[i] - lows[i]
            if full_range == 0:
                continue
            body_ratio = body / full_range

            if body_ratio > 0.6:
                vol_ratio = float(volumes[i] / np.mean(volumes)) if np.mean(volumes) > 0 else 1.0
                strength = min(body_ratio * 0.6 + min(vol_ratio, 2.0) * 0.2, 1.0)

                if closes[i] > opens[i]:
                    zones.append(
                        Zone(
                            upper=float(max(opens[i], closes[i])),
                            lower=float(lows[i]),
                            zone_type="demand",
                            strength=strength,
                        )
                    )
                else:
                    zones.append(
                        Zone(
                            upper=float(highs[i]),
                            lower=float(min(opens[i], closes[i])),
                            zone_type="supply",
                            strength=strength,
                        )
                    )
        return zones

    @staticmethod
    def _detect_imbalances(data: pd.DataFrame, min_gap: float) -> List[Imbalance]:
        imbalances: List[Imbalance] = []
        if len(data) < 3:
            return imbalances

        highs = data["high"].values
        lows = data["low"].values

        for i in range(2, len(data)):
            # Bullish FVG
            if lows[i] > highs[i - 2] and (lows[i] - highs[i - 2]) >= min_gap:
                imbalances.append(
                    Imbalance(
                        index=i,
                        upper=float(lows[i]),
                        lower=float(highs[i - 2]),
                        direction=Direction.BUY,
                    )
                )
            # Bearish FVG
            elif highs[i] < lows[i - 2] and (lows[i - 2] - highs[i]) >= min_gap:
                imbalances.append(
                    Imbalance(
                        index=i,
                        upper=float(lows[i - 2]),
                        lower=float(highs[i]),
                        direction=Direction.SELL,
                    )
                )
        return imbalances

    @staticmethod
    def _detect_liquidity_grabs(
        data: pd.DataFrame, lookback: int
    ) -> List[Direction]:
        grabs: List[Direction] = []
        if len(data) < lookback + 2:
            return grabs

        recent = data.iloc[-(lookback + 2) :]
        prev_high = recent["high"].iloc[:-2].max()
        prev_low = recent["low"].iloc[:-2].min()

        last = data.iloc[-1]
        if last["high"] > prev_high and last["close"] < prev_high:
            grabs.append(Direction.SELL)
        if last["low"] < prev_low and last["close"] > prev_low:
            grabs.append(Direction.BUY)

        return grabs
