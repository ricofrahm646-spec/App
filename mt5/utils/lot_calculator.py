"""Lot size calculation utilities for forex and CFD trading."""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AccountCurrency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    NZD = "NZD"


class SymbolCategory(Enum):
    FOREX_MAJOR = "forex_major"
    FOREX_CROSS = "forex_cross"
    FOREX_EXOTIC = "forex_exotic"
    METAL = "metal"
    INDEX = "index"
    CRYPTO = "crypto"
    COMMODITY = "commodity"


@dataclass
class SymbolSpec:
    """Specification for a tradable symbol."""
    name: str
    category: SymbolCategory
    contract_size: float = 100_000.0
    tick_size: float = 0.00001
    tick_value: float = 1.0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    digits: int = 5
    base_currency: str = "EUR"
    quote_currency: str = "USD"
    margin_rate: float = 1.0


# Pip sizes per digit count
_PIP_SIZE: Dict[int, float] = {
    2: 0.01,    # JPY pairs
    3: 0.01,    # JPY pairs (3-digit broker)
    4: 0.0001,  # Standard pairs
    5: 0.0001,  # Standard pairs (5-digit broker)
}

COMMON_SYMBOLS: Dict[str, SymbolSpec] = {
    "EURUSD": SymbolSpec("EURUSD", SymbolCategory.FOREX_MAJOR, digits=5, base_currency="EUR", quote_currency="USD"),
    "GBPUSD": SymbolSpec("GBPUSD", SymbolCategory.FOREX_MAJOR, digits=5, base_currency="GBP", quote_currency="USD"),
    "USDJPY": SymbolSpec("USDJPY", SymbolCategory.FOREX_MAJOR, digits=3, base_currency="USD", quote_currency="JPY", tick_size=0.001),
    "USDCHF": SymbolSpec("USDCHF", SymbolCategory.FOREX_MAJOR, digits=5, base_currency="USD", quote_currency="CHF"),
    "AUDUSD": SymbolSpec("AUDUSD", SymbolCategory.FOREX_MAJOR, digits=5, base_currency="AUD", quote_currency="USD"),
    "USDCAD": SymbolSpec("USDCAD", SymbolCategory.FOREX_MAJOR, digits=5, base_currency="USD", quote_currency="CAD"),
    "NZDUSD": SymbolSpec("NZDUSD", SymbolCategory.FOREX_MAJOR, digits=5, base_currency="NZD", quote_currency="USD"),
    "XAUUSD": SymbolSpec("XAUUSD", SymbolCategory.METAL, contract_size=100.0, digits=2, tick_size=0.01, base_currency="XAU", quote_currency="USD"),
    "XAGUSD": SymbolSpec("XAGUSD", SymbolCategory.METAL, contract_size=5000.0, digits=3, tick_size=0.001, base_currency="XAG", quote_currency="USD"),
    "US30":   SymbolSpec("US30", SymbolCategory.INDEX, contract_size=1.0, digits=2, tick_size=0.01, base_currency="USD", quote_currency="USD"),
    "NAS100": SymbolSpec("NAS100", SymbolCategory.INDEX, contract_size=1.0, digits=2, tick_size=0.01, base_currency="USD", quote_currency="USD"),
    "BTCUSD": SymbolSpec("BTCUSD", SymbolCategory.CRYPTO, contract_size=1.0, digits=2, tick_size=0.01, base_currency="BTC", quote_currency="USD"),
}


def pip_size(digits: int) -> float:
    """Return the pip size for a given number of price digits."""
    return _PIP_SIZE.get(digits, 0.0001)


def pip_value(
    symbol: str,
    volume: float = 1.0,
    account_currency: str = "USD",
    conversion_rate: Optional[float] = None,
    spec: Optional[SymbolSpec] = None,
) -> float:
    """Calculate the monetary value of 1 pip for the given volume.

    For a standard forex lot (100 000 units) on a USD-quoted pair, 1 pip = $10.
    For cross-pairs the result is converted via *conversion_rate* when the
    account currency differs from the quote currency.
    """
    s = spec or COMMON_SYMBOLS.get(symbol)
    if s is None:
        logger.warning("Unknown symbol %s – using default EURUSD spec", symbol)
        s = COMMON_SYMBOLS["EURUSD"]

    one_pip = pip_size(s.digits)
    value_in_quote = volume * s.contract_size * one_pip

    if s.quote_currency == account_currency:
        return round(value_in_quote, 4)

    rate = conversion_rate
    if rate is None:
        rate = _estimate_conversion(s.quote_currency, account_currency)
    return round(value_in_quote * rate, 4)


def calculate_lot_size(
    balance: float,
    risk_pct: float,
    sl_pips: float,
    symbol: str = "EURUSD",
    account_currency: str = "USD",
    conversion_rate: Optional[float] = None,
    spec: Optional[SymbolSpec] = None,
) -> float:
    """Calculate lot size from risk percentage and stop-loss distance in pips.

    Parameters
    ----------
    balance : float
        Account balance (or equity) in account currency.
    risk_pct : float
        Fraction of balance to risk (e.g. 0.01 for 1 %).
    sl_pips : float
        Stop-loss distance in pips.
    symbol : str
        Trading symbol name.
    account_currency : str
        Account denomination currency.
    conversion_rate : float | None
        Quote-currency-to-account-currency rate override.
    spec : SymbolSpec | None
        Custom symbol specification (looked up from defaults if *None*).

    Returns
    -------
    float
        Calculated lot size, clamped to symbol min/max and rounded to step.
    """
    if balance <= 0 or risk_pct <= 0 or sl_pips <= 0:
        return 0.01

    s = spec or COMMON_SYMBOLS.get(symbol)
    if s is None:
        s = COMMON_SYMBOLS["EURUSD"]

    risk_amount = balance * risk_pct
    pv = pip_value(symbol, 1.0, account_currency, conversion_rate, s)
    if pv <= 0:
        return s.volume_min

    lots = risk_amount / (sl_pips * pv)
    lots = _clamp_and_step(lots, s)
    return lots


def calculate_margin(
    symbol: str,
    volume: float,
    price: float,
    leverage: int,
    account_currency: str = "USD",
    conversion_rate: Optional[float] = None,
    spec: Optional[SymbolSpec] = None,
) -> float:
    """Calculate margin required to open a position.

    Margin = (Volume * Contract Size * Price) / Leverage  [* conversion if needed]
    """
    s = spec or COMMON_SYMBOLS.get(symbol)
    if s is None:
        s = COMMON_SYMBOLS["EURUSD"]

    if leverage <= 0:
        leverage = 1

    margin_in_base = (volume * s.contract_size * price * s.margin_rate) / leverage

    if s.quote_currency == account_currency:
        return round(margin_in_base, 2)

    rate = conversion_rate if conversion_rate is not None else _estimate_conversion(s.quote_currency, account_currency)
    return round(margin_in_base * rate, 2)


def risk_reward_ratio(sl_pips: float, tp_pips: float) -> float:
    """Return the risk:reward ratio (e.g. 2.0 means 1:2)."""
    if sl_pips <= 0:
        return 0.0
    return round(tp_pips / sl_pips, 2)


def position_value(symbol: str, volume: float, price: float, spec: Optional[SymbolSpec] = None) -> float:
    """Notional value of a position in quote currency."""
    s = spec or COMMON_SYMBOLS.get(symbol)
    if s is None:
        s = COMMON_SYMBOLS["EURUSD"]
    return round(volume * s.contract_size * price, 2)


def pips_to_price(pips: float, digits: int) -> float:
    """Convert a pip count to a price distance."""
    return round(pips * pip_size(digits), digits)


def price_to_pips(price_distance: float, digits: int) -> float:
    """Convert a price distance to pips."""
    ps = pip_size(digits)
    if ps <= 0:
        return 0.0
    return round(price_distance / ps, 1)


def _clamp_and_step(lots: float, spec: SymbolSpec) -> float:
    lots = max(spec.volume_min, min(lots, spec.volume_max))
    if spec.volume_step > 0:
        lots = round(lots / spec.volume_step) * spec.volume_step
    return round(lots, 2)


def _estimate_conversion(from_currency: str, to_currency: str) -> float:
    """Rough static conversion for when no live rate is available.

    Production systems should replace this with live rates.
    """
    if from_currency == to_currency:
        return 1.0

    approximate_to_usd: Dict[str, float] = {
        "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067,
        "CHF": 1.12, "AUD": 0.65, "CAD": 0.74, "NZD": 0.61,
        "XAU": 2350.0, "XAG": 29.0, "BTC": 68000.0,
    }

    from_usd = approximate_to_usd.get(from_currency, 1.0)
    to_usd = approximate_to_usd.get(to_currency, 1.0)
    if to_usd == 0:
        return 1.0
    return from_usd / to_usd
