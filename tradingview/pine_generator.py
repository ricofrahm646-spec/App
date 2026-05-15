"""Generate Pine Script v5 strategies + alerts for TradingView (Forex only)."""
from __future__ import annotations

from typing import Any


_TEMPLATES = {
    "trend_following": """
//@version=5
strategy("{name}", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10)

fast   = input.int({fast},   "Fast EMA")
slow   = input.int({slow},   "Slow EMA")

fastEma = ta.ema(close, fast)
slowEma = ta.ema(close, slow)

plot(fastEma, color=color.aqua, title="Fast")
plot(slowEma, color=color.orange, title="Slow")

longCond  = ta.crossover(fastEma, slowEma)
shortCond = ta.crossunder(fastEma, slowEma)

if longCond
    strategy.entry("Long", strategy.long)
if shortCond
    strategy.entry("Short", strategy.short)

alertcondition(longCond,  "BUY",  '{{"secret":"<your_secret>","symbol":"{{{{ticker}}}}","side":"BUY","volume":0.05}}')
alertcondition(shortCond, "SELL", '{{"secret":"<your_secret>","symbol":"{{{{ticker}}}}","side":"SELL","volume":0.05}}')
""",
    "breakout": """
//@version=5
strategy("{name}", overlay=true)

length = input.int({length}, "Donchian Length")
hh = ta.highest(high, length)
ll = ta.lowest(low, length)
plot(hh, color=color.green)
plot(ll, color=color.red)

longCond  = close > hh[1]
shortCond = close < ll[1]
if longCond  : strategy.entry("Long",  strategy.long)
if shortCond : strategy.entry("Short", strategy.short)
""",
    "mean_reversion": """
//@version=5
strategy("{name}", overlay=true)

length = input.int({length}, "BB length")
stdev  = input.float({stdev}, "Stdev")
basis = ta.sma(close, length)
dev   = stdev * ta.stdev(close, length)
upper = basis + dev
lower = basis - dev
plot(upper, color=color.purple)
plot(lower, color=color.purple)

if close < lower : strategy.entry("Long",  strategy.long)
if close > upper : strategy.entry("Short", strategy.short)
""",
}


class PineGenerator:
    def generate(self, name: str, kind: str = "trend_following", parameters: dict[str, Any] | None = None) -> str:
        params = parameters or {}
        tpl = _TEMPLATES.get(kind, _TEMPLATES["trend_following"])
        return tpl.format(
            name=name,
            fast=int(params.get("fast", 20)),
            slow=int(params.get("slow", 50)),
            length=int(params.get("length", 20)),
            stdev=float(params.get("stdev", 2.0)),
        ).strip()
