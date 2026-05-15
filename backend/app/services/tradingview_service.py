from typing import Any

from backend.app.models.schemas import GeneratedFile, StrategySpec
from backend.app.services.strategy_factory import StrategyFactory


class TradingViewService:
    FOREX_SUFFIXES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD")

    def validate_forex_symbol(self, symbol: str) -> bool:
        normalized = symbol.replace("/", "").upper()
        return len(normalized) == 6 and normalized[:3] in self.FOREX_SUFFIXES and normalized[3:] in self.FOREX_SUFFIXES

    def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = str(payload.get("symbol", "")).replace("/", "").upper()
        if not self.validate_forex_symbol(symbol):
            raise ValueError("TradingView integration accepts Forex pairs only")
        side = str(payload.get("side", "")).lower()
        if side not in {"buy", "sell"}:
            raise ValueError("Webhook side must be buy or sell")
        return {
            "symbol": symbol,
            "side": side,
            "price": float(payload.get("price", 0)),
            "source": "tradingview",
        }

    def pine_script(self, strategy: StrategySpec) -> GeneratedFile:
        strategy_id = StrategyFactory.strategy_id(strategy)
        content = f"""//@version=5
indicator("JARVIS {strategy.name}", overlay=true, max_labels_count=500)

fast = ta.ema(close, 9)
slow = ta.ema(close, 21)
buySignal = ta.crossover(fast, slow)
sellSignal = ta.crossunder(fast, slow)
atr = ta.atr(14)

plotshape(buySignal, title="Buy", style=shape.labelup, color=color.new(color.green, 0), text="BUY")
plotshape(sellSignal, title="Sell", style=shape.labeldown, color=color.new(color.red, 0), text="SELL")
plot(buySignal ? close - atr * 1.5 : na, title="Buy SL", color=color.red, style=plot.style_cross)
plot(buySignal ? close + atr * 3.0 : na, title="Buy TP", color=color.green, style=plot.style_cross)
plot(sellSignal ? close + atr * 1.5 : na, title="Sell SL", color=color.red, style=plot.style_cross)
plot(sellSignal ? close - atr * 3.0 : na, title="Sell TP", color=color.green, style=plot.style_cross)

alertcondition(buySignal, title="JARVIS Buy", message='{{"symbol":"{{ticker}}","side":"buy","price":{{close}}}}')
alertcondition(sellSignal, title="JARVIS Sell", message='{{"symbol":"{{ticker}}","side":"sell","price":{{close}}}}')
"""
        return GeneratedFile(
            path=f"tradingview/{strategy_id}.pine",
            language="pine",
            purpose="TradingView Forex alert script",
            content=content,
        )
