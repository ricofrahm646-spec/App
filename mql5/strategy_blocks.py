"""MQL5 strategy logic snippets — injected into the EA template by the generator."""
from __future__ import annotations

from typing import Any


def _common_open(side: str) -> str:
    if side == "BUY":
        return (
            "double price = SymbolInfoDouble(Symbol_, SYMBOL_ASK);\n"
            "double sl    = price - SL_Pips * Pip();\n"
            "double tp    = price + TP_Pips * Pip();\n"
            "trade.Buy(Lots, Symbol_, price, sl, tp, \"jarvis\");"
        )
    return (
        "double price = SymbolInfoDouble(Symbol_, SYMBOL_BID);\n"
        "double sl    = price + SL_Pips * Pip();\n"
        "double tp    = price - TP_Pips * Pip();\n"
        "trade.Sell(Lots, Symbol_, price, sl, tp, \"jarvis\");"
    )


def trend_following_logic(parameters: dict[str, Any]) -> str:
    fast = parameters.get("fast", 20)
    slow = parameters.get("slow", 50)
    return (
        f"static int fastH = iMA(Symbol_, TF, {fast}, 0, MODE_EMA, PRICE_CLOSE);\n"
        f"static int slowH = iMA(Symbol_, TF, {slow}, 0, MODE_EMA, PRICE_CLOSE);\n"
        "double fast = Ema(fastH);\n"
        "double slow = Ema(slowH);\n"
        "if(fast > slow) {\n"
        f"   {_common_open('BUY')}\n"
        "} else if(fast < slow) {\n"
        f"   {_common_open('SELL')}\n"
        "}"
    )


def scalping_logic(parameters: dict[str, Any]) -> str:
    fast = parameters.get("fast", 5)
    slow = parameters.get("slow", 13)
    return (
        f"static int fastH = iMA(Symbol_, TF, {fast}, 0, MODE_EMA, PRICE_CLOSE);\n"
        f"static int slowH = iMA(Symbol_, TF, {slow}, 0, MODE_EMA, PRICE_CLOSE);\n"
        "double fast = Ema(fastH);\n"
        "double slow = Ema(slowH);\n"
        "if(fast > slow) {\n"
        f"   {_common_open('BUY')}\n"
        "} else if(fast < slow) {\n"
        f"   {_common_open('SELL')}\n"
        "}"
    )


def breakout_logic(parameters: dict[str, Any]) -> str:
    n = parameters.get("length", 20)
    return (
        f"double upper = iHigh(Symbol_, TF, iHighest(Symbol_, TF, MODE_HIGH, {n}, 1));\n"
        f"double lower = iLow(Symbol_, TF, iLowest(Symbol_, TF, MODE_LOW, {n}, 1));\n"
        "double close = iClose(Symbol_, TF, 0);\n"
        "if(close > upper) {\n"
        f"   {_common_open('BUY')}\n"
        "} else if(close < lower) {\n"
        f"   {_common_open('SELL')}\n"
        "}"
    )


def mean_reversion_logic(parameters: dict[str, Any]) -> str:
    n = parameters.get("length", 20)
    sd = parameters.get("stdev", 2.0)
    return (
        f"static int bbH = iBands(Symbol_, TF, {n}, 0, {sd}, PRICE_CLOSE);\n"
        "double upper[], lower[], close;\n"
        "if(CopyBuffer(bbH, 1, 0, 1, upper) <= 0) return;\n"
        "if(CopyBuffer(bbH, 2, 0, 1, lower) <= 0) return;\n"
        "close = iClose(Symbol_, TF, 0);\n"
        "if(close < lower[0]) {\n"
        f"   {_common_open('BUY')}\n"
        "} else if(close > upper[0]) {\n"
        f"   {_common_open('SELL')}\n"
        "}"
    )


def momentum_logic(parameters: dict[str, Any]) -> str:
    n = parameters.get("length", 14)
    return (
        f"static int momH = iMomentum(Symbol_, TF, {n}, PRICE_CLOSE);\n"
        "double buf[]; if(CopyBuffer(momH, 0, 0, 1, buf) <= 0) return;\n"
        "if(buf[0] > 100.15) {\n"
        f"   {_common_open('BUY')}\n"
        "} else if(buf[0] < 99.85) {\n"
        f"   {_common_open('SELL')}\n"
        "}"
    )


def ict_logic(parameters: dict[str, Any]) -> str:
    n = parameters.get("swing_lookback", 20)
    return (
        f"double swingHigh = iHigh(Symbol_, TF, iHighest(Symbol_, TF, MODE_HIGH, {n}, 1));\n"
        f"double swingLow  = iLow(Symbol_, TF, iLowest(Symbol_, TF, MODE_LOW, {n}, 1));\n"
        "double mid = (swingHigh + swingLow) / 2.0;\n"
        "double close = iClose(Symbol_, TF, 0);\n"
        "double prevHigh = iHigh(Symbol_, TF, 1);\n"
        "double prevLow  = iLow(Symbol_, TF, 1);\n"
        "if(prevLow < swingLow && close > swingLow && close <= mid) {\n"
        f"   {_common_open('BUY')}\n"
        "} else if(prevHigh > swingHigh && close < swingHigh && close >= mid) {\n"
        f"   {_common_open('SELL')}\n"
        "}"
    )


def session_logic(parameters: dict[str, Any]) -> str:
    start_h = parameters.get("session_start_h", 7)
    end_h = parameters.get("session_end_h", 16)
    return (
        "MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);\n"
        f"if(dt.hour < {start_h} || dt.hour > {end_h}) return;\n"
        + trend_following_logic({"fast": 8, "slow": 21})
    )


_DISPATCH = {
    "trend_following": trend_following_logic,
    "scalping": scalping_logic,
    "breakout": breakout_logic,
    "mean_reversion": mean_reversion_logic,
    "momentum": momentum_logic,
    "ict": ict_logic,
    "smart_money": breakout_logic,  # close cousin
    "session_trading": session_logic,
}


def build(kind: str, parameters: dict[str, Any]) -> str:
    fn = _DISPATCH.get(kind, trend_following_logic)
    return fn(parameters)
