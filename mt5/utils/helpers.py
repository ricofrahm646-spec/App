"""
JARVIS Trading OS - MT5 Utility Helpers
Pip calculation, point conversion, timeframe mapping, and general utilities.
"""

from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional

import MetaTrader5 as mt5

logger = logging.getLogger("jarvis.mt5.helpers")


class MT5Timeframe(IntEnum):
    """Mapping of human-readable timeframe names to MT5 constants."""
    M1 = mt5.TIMEFRAME_M1
    M2 = mt5.TIMEFRAME_M2
    M3 = mt5.TIMEFRAME_M3
    M4 = mt5.TIMEFRAME_M4
    M5 = mt5.TIMEFRAME_M5
    M6 = mt5.TIMEFRAME_M6
    M10 = mt5.TIMEFRAME_M10
    M12 = mt5.TIMEFRAME_M12
    M15 = mt5.TIMEFRAME_M15
    M20 = mt5.TIMEFRAME_M20
    M30 = mt5.TIMEFRAME_M30
    H1 = mt5.TIMEFRAME_H1
    H2 = mt5.TIMEFRAME_H2
    H3 = mt5.TIMEFRAME_H3
    H4 = mt5.TIMEFRAME_H4
    H6 = mt5.TIMEFRAME_H6
    H8 = mt5.TIMEFRAME_H8
    H12 = mt5.TIMEFRAME_H12
    D1 = mt5.TIMEFRAME_D1
    W1 = mt5.TIMEFRAME_W1
    MN1 = mt5.TIMEFRAME_MN1


TIMEFRAME_STRING_MAP: dict[str, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


def resolve_timeframe(tf: str | int) -> int:
    """Resolve a timeframe string or int to the MT5 constant.

    Args:
        tf: Timeframe as a string (e.g. "H1") or MT5 integer constant.

    Returns:
        MT5 timeframe constant.

    Raises:
        ValueError: If the timeframe string is not recognised.
    """
    if isinstance(tf, int):
        return tf
    key = tf.upper().strip()
    if key not in TIMEFRAME_STRING_MAP:
        raise ValueError(
            f"Unknown timeframe '{tf}'. Valid values: {list(TIMEFRAME_STRING_MAP.keys())}"
        )
    return TIMEFRAME_STRING_MAP[key]


def is_jpy_pair(symbol: str) -> bool:
    """Return True when the symbol is a JPY cross (3-digit pricing)."""
    return "JPY" in symbol.upper()


def pip_value(symbol: str, point: float, digits: int) -> float:
    """Return the value of 1 pip for *symbol* in terms of its price unit.

    For 5/3-digit brokers a pip is 10 points for standard pairs and
    10 points for JPY pairs as well (the *digits* parameter disambiguates).

    Args:
        symbol: Instrument name.
        point: The symbol's ``point`` value from ``mt5.symbol_info``.
        digits: The symbol's ``digits`` value.

    Returns:
        Price delta representing 1 pip.
    """
    if digits in (3, 5):
        return point * 10
    return point


def pips_to_price(symbol: str, pips: float, point: float, digits: int) -> float:
    """Convert a pip distance to a price delta.

    Args:
        symbol: Instrument name.
        pips: Number of pips.
        point: Symbol point.
        digits: Symbol digits.

    Returns:
        Price delta equivalent to *pips* pips.
    """
    return pips * pip_value(symbol, point, digits)


def price_to_pips(symbol: str, price_delta: float, point: float, digits: int) -> float:
    """Convert a price delta to pips.

    Args:
        symbol: Instrument name.
        price_delta: Absolute price difference.
        point: Symbol point.
        digits: Symbol digits.

    Returns:
        Number of pips.
    """
    pv = pip_value(symbol, point, digits)
    if pv == 0:
        return 0.0
    return abs(price_delta) / pv


def normalize_price(price: float, digits: int) -> float:
    """Round *price* to the symbol's digit precision.

    Args:
        price: Raw price.
        digits: Number of decimal digits for the symbol.

    Returns:
        Normalised price.
    """
    return round(price, digits)


def calculate_lot_size(
    balance: float,
    risk_percent: float,
    sl_pips: float,
    pip_value_per_lot: float,
    min_lot: float = 0.01,
    max_lot: float = 100.0,
    lot_step: float = 0.01,
) -> float:
    """Calculate position size based on fixed-percentage risk.

    Args:
        balance: Account balance in deposit currency.
        risk_percent: Maximum risk as a percentage (e.g. 1.0 for 1 %).
        sl_pips: Stop-loss distance in pips.
        pip_value_per_lot: Monetary value of 1 pip for 1 standard lot.
        min_lot: Broker minimum lot.
        max_lot: Broker maximum lot.
        lot_step: Broker lot step.

    Returns:
        Lot size rounded to the nearest valid step.
    """
    if sl_pips <= 0 or pip_value_per_lot <= 0:
        logger.warning("Invalid sl_pips=%s or pip_value_per_lot=%s; returning min_lot", sl_pips, pip_value_per_lot)
        return min_lot

    risk_amount = balance * (risk_percent / 100.0)
    raw_lots = risk_amount / (sl_pips * pip_value_per_lot)

    steps = math.floor(raw_lots / lot_step)
    lots = steps * lot_step
    lots = max(min_lot, min(lots, max_lot))
    return round(lots, 8)


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def timestamp_ms() -> int:
    """Return the current UTC time as milliseconds since epoch."""
    return int(utc_now().timestamp() * 1000)


def trade_comment(strategy: str = "JARVIS", extra: str = "") -> str:
    """Build a standardised trade comment string.

    Args:
        strategy: Strategy label.
        extra: Optional extra info appended after the timestamp.

    Returns:
        Comment string, e.g. ``JARVIS|20260515-131200|scalp``.
    """
    ts = utc_now().strftime("%Y%m%d-%H%M%S")
    parts = [strategy, ts]
    if extra:
        parts.append(extra)
    return "|".join(parts)


def order_type_to_string(order_type: int) -> str:
    """Convert an MT5 order type constant to a human-readable label."""
    mapping = {
        mt5.ORDER_TYPE_BUY: "BUY",
        mt5.ORDER_TYPE_SELL: "SELL",
        mt5.ORDER_TYPE_BUY_LIMIT: "BUY_LIMIT",
        mt5.ORDER_TYPE_SELL_LIMIT: "SELL_LIMIT",
        mt5.ORDER_TYPE_BUY_STOP: "BUY_STOP",
        mt5.ORDER_TYPE_SELL_STOP: "SELL_STOP",
    }
    return mapping.get(order_type, f"UNKNOWN({order_type})")


def opposite_order_type(order_type: int) -> int:
    """Return the opposite order type needed to close a position.

    Args:
        order_type: ``mt5.ORDER_TYPE_BUY`` or ``mt5.ORDER_TYPE_SELL``.

    Returns:
        The closing order type.

    Raises:
        ValueError: If order_type is not BUY or SELL.
    """
    if order_type == mt5.ORDER_TYPE_BUY:
        return mt5.ORDER_TYPE_SELL
    if order_type == mt5.ORDER_TYPE_SELL:
        return mt5.ORDER_TYPE_BUY
    raise ValueError(f"Cannot determine opposite for order_type={order_type}")


def spread_in_pips(symbol_info) -> float:
    """Return the current spread in pips from a ``SymbolInfo`` namedtuple.

    Args:
        symbol_info: Object returned by ``mt5.symbol_info()``.

    Returns:
        Spread expressed in pips.
    """
    spread_points = symbol_info.spread
    pv = pip_value(symbol_info.name, symbol_info.point, symbol_info.digits)
    if pv == 0:
        return 0.0
    return (spread_points * symbol_info.point) / pv


def format_currency(amount: float, decimals: int = 2) -> str:
    """Format a monetary amount with thousand separators."""
    return f"{amount:,.{decimals}f}"
