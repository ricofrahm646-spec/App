"""
JARVIS AI Trading OS - Market Analyzer

Detects market phases, support/resistance, liquidity zones, order blocks,
and trading sessions using technical indicators.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum, auto
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class MarketPhase(Enum):
    TRENDING_UP = auto()
    TRENDING_DOWN = auto()
    RANGING = auto()
    VOLATILE = auto()
    QUIET = auto()


class Session(Enum):
    ASIAN = auto()
    LONDON = auto()
    NEW_YORK = auto()
    OFF_SESSION = auto()


@dataclass
class SupportResistance:
    price: float
    strength: int
    is_support: bool
    touches: int = 0

    @property
    def level_type(self) -> str:
        return "support" if self.is_support else "resistance"


@dataclass
class LiquidityZone:
    high: float
    low: float
    volume: float
    strength: float
    swept: bool = False


@dataclass
class OrderBlock:
    high: float
    low: float
    direction: str
    index: int
    valid: bool = True
    mitigated: bool = False


@dataclass
class MarketState:
    phase: MarketPhase
    adx: float
    atr: float
    bb_width: float
    trend_strength: float
    support_levels: list[SupportResistance] = field(default_factory=list)
    resistance_levels: list[SupportResistance] = field(default_factory=list)
    liquidity_zones: list[LiquidityZone] = field(default_factory=list)
    order_blocks: list[OrderBlock] = field(default_factory=list)
    session: Session = Session.OFF_SESSION


# ---------------------------------------------------------------------------
# Session definitions (UTC)
# ---------------------------------------------------------------------------

_SESSION_TIMES: dict[Session, tuple[time, time]] = {
    Session.ASIAN: (time(0, 0), time(9, 0)),
    Session.LONDON: (time(7, 0), time(16, 0)),
    Session.NEW_YORK: (time(12, 0), time(21, 0)),
}


# ---------------------------------------------------------------------------
# Market Analyzer
# ---------------------------------------------------------------------------

class MarketAnalyzer:
    """Comprehensive market analysis engine."""

    def __init__(
        self,
        adx_period: int = 14,
        atr_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        sr_lookback: int = 100,
        sr_tolerance: float = 0.001,
        adx_trend_threshold: float = 25.0,
        atr_volatile_multiplier: float = 1.5,
        atr_quiet_multiplier: float = 0.5,
    ) -> None:
        self.adx_period = adx_period
        self.atr_period = atr_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.sr_lookback = sr_lookback
        self.sr_tolerance = sr_tolerance
        self.adx_trend_threshold = adx_trend_threshold
        self.atr_volatile_mult = atr_volatile_multiplier
        self.atr_quiet_mult = atr_quiet_multiplier

    # ----- public API -----

    def analyse(self, df: pd.DataFrame, current_time: Optional[datetime] = None) -> MarketState:
        df = self._ensure_columns(df)
        adx_val = self._adx(df, self.adx_period)
        atr_val = self._atr(df, self.atr_period)
        bb_w = self._bollinger_width(df, self.bb_period, self.bb_std)

        phase = self._detect_phase(df, adx_val, atr_val, bb_w)
        supports, resistances = self._support_resistance(df)
        liq_zones = self._liquidity_zones(df)
        obs = self._order_blocks(df)
        session = self._detect_session(current_time) if current_time else Session.OFF_SESSION

        trend_strength = self._trend_strength(df, adx_val)

        return MarketState(
            phase=phase,
            adx=round(adx_val, 2),
            atr=round(atr_val, 6),
            bb_width=round(bb_w, 6),
            trend_strength=round(trend_strength, 2),
            support_levels=supports,
            resistance_levels=resistances,
            liquidity_zones=liq_zones,
            order_blocks=obs,
            session=session,
        )

    def detect_phase(self, df: pd.DataFrame) -> MarketPhase:
        df = self._ensure_columns(df)
        adx_val = self._adx(df, self.adx_period)
        atr_val = self._atr(df, self.atr_period)
        bb_w = self._bollinger_width(df, self.bb_period, self.bb_std)
        return self._detect_phase(df, adx_val, atr_val, bb_w)

    def get_support_resistance(self, df: pd.DataFrame) -> tuple[list[SupportResistance], list[SupportResistance]]:
        df = self._ensure_columns(df)
        return self._support_resistance(df)

    def get_liquidity_zones(self, df: pd.DataFrame) -> list[LiquidityZone]:
        df = self._ensure_columns(df)
        return self._liquidity_zones(df)

    def get_order_blocks(self, df: pd.DataFrame) -> list[OrderBlock]:
        df = self._ensure_columns(df)
        return self._order_blocks(df)

    def detect_session(self, dt: datetime) -> Session:
        return self._detect_session(dt)

    # ----- indicator calculations -----

    @staticmethod
    def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
        required = {"open", "high", "low", "close"}
        cols = {c.lower() for c in df.columns}
        if not required.issubset(cols):
            raise ValueError(f"DataFrame must contain columns: {required}")
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        return df

    @staticmethod
    def _atr(df: pd.DataFrame, period: int) -> float:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_series = tr.rolling(window=period).mean()
        return float(atr_series.iloc[-1]) if not atr_series.empty else 0.0

    @staticmethod
    def _adx(df: pd.DataFrame, period: int) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr_h_l = high - low
        tr_h_c = (high - close.shift()).abs()
        tr_l_c = (low - close.shift()).abs()
        tr = pd.concat([tr_h_l, tr_h_c, tr_l_c], axis=1).max(axis=1)

        atr_series = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr_series)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr_series)

        dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
        adx_series = dx.ewm(span=period, adjust=False).mean()
        return float(adx_series.iloc[-1]) if not adx_series.empty else 0.0

    @staticmethod
    def _bollinger_width(df: pd.DataFrame, period: int, num_std: float) -> float:
        ma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()
        upper = ma + num_std * std
        lower = ma - num_std * std
        width = (upper - lower) / ma
        return float(width.iloc[-1]) if not width.empty else 0.0

    def _detect_phase(
        self, df: pd.DataFrame, adx: float, atr: float, bb_width: float,
    ) -> MarketPhase:
        atr_ma = df["close"].rolling(self.atr_period).apply(
            lambda x: (x.diff().abs().mean()) if len(x) > 1 else 0.0, raw=False,
        )
        avg_atr = float(atr_ma.iloc[-1]) if not atr_ma.empty else atr

        if adx > self.adx_trend_threshold:
            ema20 = df["close"].ewm(span=20, adjust=False).mean()
            if df["close"].iloc[-1] > ema20.iloc[-1]:
                return MarketPhase.TRENDING_UP
            return MarketPhase.TRENDING_DOWN

        if avg_atr > 0 and atr > avg_atr * self.atr_volatile_mult:
            return MarketPhase.VOLATILE

        if avg_atr > 0 and atr < avg_atr * self.atr_quiet_mult:
            return MarketPhase.QUIET

        return MarketPhase.RANGING

    @staticmethod
    def _trend_strength(df: pd.DataFrame, adx: float) -> float:
        ema_fast = df["close"].ewm(span=8, adjust=False).mean()
        ema_slow = df["close"].ewm(span=21, adjust=False).mean()
        diff = float(ema_fast.iloc[-1] - ema_slow.iloc[-1])
        price = float(df["close"].iloc[-1])
        directional = (diff / price * 100) if price else 0.0
        return min(100.0, abs(directional) * 10 + adx)

    # ----- support / resistance -----

    def _support_resistance(
        self, df: pd.DataFrame,
    ) -> tuple[list[SupportResistance], list[SupportResistance]]:
        window = min(self.sr_lookback, len(df))
        segment = df.iloc[-window:]
        highs = segment["high"].values
        lows = segment["low"].values
        close_now = float(segment["close"].iloc[-1])

        pivot_highs = self._find_pivots(highs, is_high=True)
        pivot_lows = self._find_pivots(lows, is_high=False)

        supports: list[SupportResistance] = []
        resistances: list[SupportResistance] = []

        levels_seen: set[float] = set()
        tol = close_now * self.sr_tolerance

        for price in pivot_lows:
            rounded = round(price, 5)
            if any(abs(rounded - s) < tol for s in levels_seen):
                for sr in supports:
                    if abs(sr.price - rounded) < tol:
                        sr.touches += 1
                        sr.strength += 1
                continue
            levels_seen.add(rounded)
            supports.append(SupportResistance(price=rounded, strength=1, is_support=True, touches=1))

        for price in pivot_highs:
            rounded = round(price, 5)
            if any(abs(rounded - s) < tol for s in levels_seen):
                for sr in resistances:
                    if abs(sr.price - rounded) < tol:
                        sr.touches += 1
                        sr.strength += 1
                continue
            levels_seen.add(rounded)
            resistances.append(SupportResistance(price=rounded, strength=1, is_support=False, touches=1))

        supports.sort(key=lambda s: s.price, reverse=True)
        resistances.sort(key=lambda s: s.price)

        return supports[:10], resistances[:10]

    @staticmethod
    def _find_pivots(data: np.ndarray, is_high: bool, order: int = 5) -> list[float]:
        pivots: list[float] = []
        for i in range(order, len(data) - order):
            window = data[i - order: i + order + 1]
            if is_high and data[i] == window.max():
                pivots.append(float(data[i]))
            elif not is_high and data[i] == window.min():
                pivots.append(float(data[i]))
        return pivots

    # ----- liquidity zones -----

    def _liquidity_zones(self, df: pd.DataFrame, n_zones: int = 5) -> list[LiquidityZone]:
        if "volume" not in df.columns:
            return []

        window = min(self.sr_lookback, len(df))
        segment = df.iloc[-window:]

        price_range = segment["high"].max() - segment["low"].min()
        if price_range == 0:
            return []

        n_bins = 50
        bin_size = price_range / n_bins
        bins: list[dict[str, float]] = []

        low_min = float(segment["low"].min())
        for i in range(n_bins):
            bin_low = low_min + i * bin_size
            bin_high = bin_low + bin_size
            mask = (segment["low"] <= bin_high) & (segment["high"] >= bin_low)
            vol = float(segment.loc[mask, "volume"].sum())
            bins.append({"low": bin_low, "high": bin_high, "volume": vol})

        bins.sort(key=lambda b: b["volume"], reverse=True)
        max_vol = bins[0]["volume"] if bins else 1.0

        zones: list[LiquidityZone] = []
        for b in bins[:n_zones]:
            zones.append(LiquidityZone(
                high=round(b["high"], 5),
                low=round(b["low"], 5),
                volume=b["volume"],
                strength=round(b["volume"] / max_vol, 2) if max_vol else 0.0,
            ))

        return zones

    # ----- order blocks (ICT concept) -----

    @staticmethod
    def _order_blocks(df: pd.DataFrame, lookback: int = 50) -> list[OrderBlock]:
        segment = df.iloc[-lookback:].reset_index(drop=True)
        blocks: list[OrderBlock] = []

        for i in range(2, len(segment)):
            prev = segment.iloc[i - 1]
            curr = segment.iloc[i]

            if curr["close"] > curr["open"] and prev["close"] < prev["open"]:
                body_ratio = abs(curr["close"] - curr["open"])
                prev_range = prev["high"] - prev["low"]
                if prev_range > 0 and body_ratio / prev_range > 0.5:
                    blocks.append(OrderBlock(
                        high=round(float(prev["high"]), 5),
                        low=round(float(prev["low"]), 5),
                        direction="bullish",
                        index=i - 1,
                    ))

            if curr["close"] < curr["open"] and prev["close"] > prev["open"]:
                body_ratio = abs(curr["open"] - curr["close"])
                prev_range = prev["high"] - prev["low"]
                if prev_range > 0 and body_ratio / prev_range > 0.5:
                    blocks.append(OrderBlock(
                        high=round(float(prev["high"]), 5),
                        low=round(float(prev["low"]), 5),
                        direction="bearish",
                        index=i - 1,
                    ))

        current_price = float(segment["close"].iloc[-1])
        for ob in blocks:
            if ob.direction == "bullish" and current_price < ob.low:
                ob.mitigated = True
            elif ob.direction == "bearish" and current_price > ob.high:
                ob.mitigated = True

        return [ob for ob in blocks if not ob.mitigated][-10:]

    # ----- session detection -----

    @staticmethod
    def _detect_session(dt: datetime) -> Session:
        t = dt.time()
        for session, (start, end) in _SESSION_TIMES.items():
            if start <= end:
                if start <= t <= end:
                    return session
            else:
                if t >= start or t <= end:
                    return session
        return Session.OFF_SESSION
