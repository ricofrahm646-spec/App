"""
core.smc
========
Smart Money Concepts engine - pure-Python, no broker dependency.

Implements the classic ICT/SMC building blocks used by JARVIS V300:

  * Swing-high / swing-low detection (fractals)
  * Break-of-Structure (BOS) and Change-of-Character (CHoCH)
  * Bullish & bearish Order Blocks
  * Fair-Value-Gaps (FVG, 3-bar imbalances)
  * Liquidity pools (equal highs/lows) and liquidity sweeps (stop hunts)
  * Premium / Discount zones (50% of the dealing range)
  * ATR for volatility-aware stops
  * Confluence scoring 0..1 that fuses everything

All public functions accept an OHLC pandas DataFrame with columns
``open, high, low, close`` (and optionally ``time`` / ``volume``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

import numpy as np
import pandas as pd

Direction = Literal["BUY", "SELL", "NONE"]


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
@dataclass
class Swing:
    index: int
    price: float
    kind: Literal["HIGH", "LOW"]


@dataclass
class OrderBlock:
    index: int
    high: float
    low: float
    direction: Direction          # BUY = bullish OB, SELL = bearish OB
    mitigated: bool = False


@dataclass
class FVG:
    index: int
    top: float
    bottom: float
    direction: Direction
    filled: bool = False


@dataclass
class LiquidityPool:
    price: float
    direction: Literal["BSL", "SSL"]   # Buy-side / Sell-side liquidity
    indexes: List[int] = field(default_factory=list)


@dataclass
class StructureState:
    last_bos: Direction = "NONE"
    last_choch: Direction = "NONE"
    last_swing_high: Optional[Swing] = None
    last_swing_low: Optional[Swing] = None


@dataclass
class MarketStructure:
    swings: List[Swing]
    state: StructureState
    order_blocks: List[OrderBlock]
    fvgs: List[FVG]
    liquidity: List[LiquidityPool]
    sweep: Direction
    premium_discount: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]
    atr: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def atr(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 1:
        return float((df["high"] - df["low"]).mean() or 0.0)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def find_swings(df: pd.DataFrame, left: int = 2, right: int = 2) -> List[Swing]:
    """Williams-style fractal swing detection."""
    swings: List[Swing] = []
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    for i in range(left, n - right):
        window_h = highs[i - left:i + right + 1]
        window_l = lows[i - left:i + right + 1]
        if highs[i] == window_h.max() and (window_h == highs[i]).sum() == 1:
            swings.append(Swing(index=i, price=float(highs[i]), kind="HIGH"))
        elif lows[i] == window_l.min() and (window_l == lows[i]).sum() == 1:
            swings.append(Swing(index=i, price=float(lows[i]), kind="LOW"))
    return swings


def detect_structure(df: pd.DataFrame, swings: List[Swing]) -> StructureState:
    """Walk the swings to determine the most recent BOS / CHoCH."""
    state = StructureState()
    last_dir: Direction = "NONE"
    last_high: Optional[Swing] = None
    last_low: Optional[Swing] = None
    prev_high: Optional[Swing] = None
    prev_low: Optional[Swing] = None
    close = df["close"].values

    for sw in swings:
        if sw.kind == "HIGH":
            prev_high, last_high = last_high, sw
            if prev_high and sw.price > prev_high.price:
                if last_dir == "SELL":
                    state.last_choch = "BUY"
                state.last_bos = "BUY"
                last_dir = "BUY"
        else:
            prev_low, last_low = last_low, sw
            if prev_low and sw.price < prev_low.price:
                if last_dir == "BUY":
                    state.last_choch = "SELL"
                state.last_bos = "SELL"
                last_dir = "SELL"

    # Confirm BOS with the latest close vs last swing
    if last_high and close[-1] > last_high.price and state.last_bos != "BUY":
        state.last_bos = "BUY"
    if last_low and close[-1] < last_low.price and state.last_bos != "SELL":
        state.last_bos = "SELL"

    state.last_swing_high = last_high
    state.last_swing_low = last_low
    return state


def detect_order_blocks(df: pd.DataFrame, swings: List[Swing], lookback: int = 8) -> List[OrderBlock]:
    """An order block is the last opposite-coloured candle before an impulsive
    move that breaks structure. We approximate that by scanning back from each
    swing for the most recent opposing candle."""
    obs: List[OrderBlock] = []
    o, h, l, c = (df[col].values for col in ("open", "high", "low", "close"))
    for sw in swings[-12:]:
        if sw.kind == "HIGH":
            for j in range(sw.index, max(sw.index - lookback, 0) - 1, -1):
                if c[j] < o[j]:   # bearish candle before the rally -> bullish OB? No - bearish OB above
                    obs.append(OrderBlock(index=j, high=float(h[j]), low=float(l[j]), direction="SELL"))
                    break
        else:
            for j in range(sw.index, max(sw.index - lookback, 0) - 1, -1):
                if c[j] > o[j]:
                    obs.append(OrderBlock(index=j, high=float(h[j]), low=float(l[j]), direction="BUY"))
                    break

    last_price = float(c[-1])
    for ob in obs:
        if ob.direction == "BUY" and last_price < ob.low:
            ob.mitigated = True
        elif ob.direction == "SELL" and last_price > ob.high:
            ob.mitigated = True
    return obs[-6:]


def detect_fvgs(df: pd.DataFrame, lookback: int = 100) -> List[FVG]:
    """3-bar Fair Value Gap detection."""
    out: List[FVG] = []
    h = df["high"].values
    l = df["low"].values
    start = max(2, len(df) - lookback)
    for i in range(start, len(df)):
        # Bullish FVG: low[i] > high[i-2]
        if l[i] > h[i - 2]:
            out.append(FVG(index=i, top=float(l[i]), bottom=float(h[i - 2]), direction="BUY"))
        # Bearish FVG: high[i] < low[i-2]
        elif h[i] < l[i - 2]:
            out.append(FVG(index=i, top=float(l[i - 2]), bottom=float(h[i]), direction="SELL"))

    last_price = float(df["close"].iloc[-1])
    for fvg in out:
        if fvg.bottom <= last_price <= fvg.top:
            fvg.filled = True
    return out[-8:]


def detect_liquidity(swings: List[Swing], tolerance: float = 0.0008) -> List[LiquidityPool]:
    """Cluster swings whose prices are within `tolerance` (relative)."""
    pools: List[LiquidityPool] = []
    highs = [s for s in swings if s.kind == "HIGH"]
    lows = [s for s in swings if s.kind == "LOW"]

    def _cluster(items: List[Swing], side: Literal["BSL", "SSL"]) -> None:
        used = set()
        for i, a in enumerate(items):
            if i in used:
                continue
            group = [a]
            for j in range(i + 1, len(items)):
                if j in used:
                    continue
                if abs(items[j].price - a.price) / max(a.price, 1e-9) <= tolerance:
                    group.append(items[j])
                    used.add(j)
            if len(group) >= 2:
                avg = sum(s.price for s in group) / len(group)
                pools.append(LiquidityPool(price=avg, direction=side, indexes=[s.index for s in group]))

    _cluster(highs, "BSL")
    _cluster(lows, "SSL")
    return pools


def detect_sweep(df: pd.DataFrame, liquidity: List[LiquidityPool]) -> Direction:
    """A sweep occurs when price wicks past a liquidity pool then closes back
    inside the range - classic stop-hunt then reversal signature."""
    if df.empty or not liquidity:
        return "NONE"
    last = df.iloc[-1]
    high, low, close = float(last["high"]), float(last["low"]), float(last["close"])
    for pool in liquidity:
        if pool.direction == "BSL" and high > pool.price and close < pool.price:
            return "SELL"                   # swept buy-side -> bearish setup
        if pool.direction == "SSL" and low < pool.price and close > pool.price:
            return "BUY"                    # swept sell-side -> bullish setup
    return "NONE"


def premium_discount(df: pd.DataFrame, state: StructureState) -> str:
    if not state.last_swing_high or not state.last_swing_low:
        return "EQUILIBRIUM"
    hi = state.last_swing_high.price
    lo = state.last_swing_low.price
    if hi <= lo:
        return "EQUILIBRIUM"
    mid = (hi + lo) / 2.0
    close = float(df["close"].iloc[-1])
    if close > mid + (hi - lo) * 0.05:
        return "PREMIUM"
    if close < mid - (hi - lo) * 0.05:
        return "DISCOUNT"
    return "EQUILIBRIUM"


# ---------------------------------------------------------------------------
# High-level analysis
# ---------------------------------------------------------------------------
def analyze(df: pd.DataFrame) -> MarketStructure:
    df = df.copy().reset_index(drop=True)
    swings = find_swings(df)
    state = detect_structure(df, swings)
    obs = detect_order_blocks(df, swings)
    fvgs = detect_fvgs(df)
    liq = detect_liquidity(swings)
    sweep = detect_sweep(df, liq)
    pd_zone = premium_discount(df, state)
    _atr = atr(df)
    return MarketStructure(
        swings=swings,
        state=state,
        order_blocks=obs,
        fvgs=fvgs,
        liquidity=liq,
        sweep=sweep,
        premium_discount=pd_zone,
        atr=_atr,
    )


# ---------------------------------------------------------------------------
# Confluence scoring
# ---------------------------------------------------------------------------
@dataclass
class Confluence:
    direction: Direction
    score: float                  # 0..1
    reasons: List[str] = field(default_factory=list)


def score_confluence(
    ltf: MarketStructure,
    htf_bias: Direction,
    price: float,
) -> Confluence:
    """Fuse LTF SMC structure with HTF bias into a 0..1 confluence score.

    Weights (must sum to 1.0):
        HTF bias agreement ............... 0.25
        LTF BOS / CHoCH agreement ........ 0.20
        Liquidity sweep present .......... 0.15
        Price inside unmitigated OB ...... 0.15
        Price inside unfilled FVG ........ 0.10
        Premium/Discount alignment ....... 0.10
        Volatility sane (ATR>0) .......... 0.05
    """
    reasons: List[str] = []
    bull = 0.0
    bear = 0.0

    # HTF
    if htf_bias == "BUY":
        bull += 0.25
        reasons.append("HTF bias bullish")
    elif htf_bias == "SELL":
        bear += 0.25
        reasons.append("HTF bias bearish")

    # LTF BOS / CHoCH
    if ltf.state.last_bos == "BUY":
        bull += 0.12
        reasons.append("LTF BOS bullish")
    elif ltf.state.last_bos == "SELL":
        bear += 0.12
        reasons.append("LTF BOS bearish")
    if ltf.state.last_choch == "BUY":
        bull += 0.08
        reasons.append("CHoCH bullish")
    elif ltf.state.last_choch == "SELL":
        bear += 0.08
        reasons.append("CHoCH bearish")

    # Liquidity sweep
    if ltf.sweep == "BUY":
        bull += 0.15
        reasons.append("Sell-side liquidity swept")
    elif ltf.sweep == "SELL":
        bear += 0.15
        reasons.append("Buy-side liquidity swept")

    # Order block alignment
    for ob in ltf.order_blocks:
        if ob.mitigated:
            continue
        if ob.direction == "BUY" and ob.low <= price <= ob.high * 1.001:
            bull += 0.15
            reasons.append("Inside bullish OB")
            break
        if ob.direction == "SELL" and ob.low * 0.999 <= price <= ob.high:
            bear += 0.15
            reasons.append("Inside bearish OB")
            break

    # FVG alignment
    for fvg in ltf.fvgs:
        if fvg.filled:
            continue
        if fvg.direction == "BUY" and fvg.bottom <= price <= fvg.top:
            bull += 0.10
            reasons.append("Inside bullish FVG")
            break
        if fvg.direction == "SELL" and fvg.bottom <= price <= fvg.top:
            bear += 0.10
            reasons.append("Inside bearish FVG")
            break

    # Premium/Discount: longs in discount, shorts in premium
    if ltf.premium_discount == "DISCOUNT":
        bull += 0.10
        reasons.append("Discount zone")
    elif ltf.premium_discount == "PREMIUM":
        bear += 0.10
        reasons.append("Premium zone")

    # Sanity
    if ltf.atr > 0:
        bull += 0.025
        bear += 0.025

    bull = float(np.clip(bull, 0.0, 1.0))
    bear = float(np.clip(bear, 0.0, 1.0))

    if bull > bear:
        return Confluence(direction="BUY", score=bull, reasons=reasons)
    if bear > bull:
        return Confluence(direction="SELL", score=bear, reasons=reasons)
    return Confluence(direction="NONE", score=0.0, reasons=reasons)


def htf_bias(df_htf: pd.DataFrame) -> Direction:
    """A simple but robust HTF bias filter: EMA50 vs EMA200 + last close."""
    if len(df_htf) < 50:
        return "NONE"
    close = df_htf["close"].astype(float)
    ema_fast = close.ewm(span=50, adjust=False).mean().iloc[-1]
    ema_slow = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(close) >= 200 else ema_fast
    last = float(close.iloc[-1])
    if last > ema_fast and ema_fast >= ema_slow:
        return "BUY"
    if last < ema_fast and ema_fast <= ema_slow:
        return "SELL"
    return "NONE"


__all__ = [
    "Direction",
    "Swing",
    "OrderBlock",
    "FVG",
    "LiquidityPool",
    "StructureState",
    "MarketStructure",
    "Confluence",
    "atr",
    "find_swings",
    "detect_structure",
    "detect_order_blocks",
    "detect_fvgs",
    "detect_liquidity",
    "detect_sweep",
    "premium_discount",
    "analyze",
    "score_confluence",
    "htf_bias",
]
