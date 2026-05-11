"""Portfolio allocation agent distributing exposure across symbols."""

from __future__ import annotations

from statistics import pstdev
from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class PortfolioAllocatorAgent(BaseTradingAgent):
    """Builds allocation-aware decisions based on relative volatility."""

    keywords = ("portfolio", "allocation", "exposure", "multi symbol", "rebalance")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        symbols = [symbol, "EURUSD", "GBPUSD", "USDJPY"]
        unique_symbols = list(dict.fromkeys(symbols))
        vol_map: dict[str, float] = {}
        mom_map: dict[str, float] = {}
        for item in unique_symbols:
            response = await self.gateway.copy_rates(item, timeframe=self.default_timeframe, count=200)
            if not response.get("ok"):
                continue
            closes = [row["close"] for row in response["rates"][-80:]]
            returns = [
                (closes[i] - closes[i - 1]) / closes[i - 1]
                for i in range(1, len(closes))
                if closes[i - 1] != 0
            ]
            vol_map[item] = pstdev(returns) if len(returns) > 2 else 0.0
            mom_map[item] = closes[-1] - closes[-12]

        if not vol_map:
            return {"strategy": "portfolio_allocator", "error": "no_symbols_available", "trade_decision": None}

        best_symbol = max(unique_symbols, key=lambda key: mom_map.get(key, -1e9) / (vol_map.get(key, 1e-8) + 1e-8))
        direction = "buy" if mom_map.get(best_symbol, 0.0) >= 0 else "sell"
        vol = vol_map.get(best_symbol, 0.0)
        volume = max(0.01, round(0.04 / (vol * 1000 + 1), 2))

        decision = TradeDecision(
            symbol=best_symbol,
            side=direction,
            volume=volume,
            sl_points=150,
            tp_points=270,
            comment="PortfolioAllocator",
            confidence=0.67,
        )
        return {
            "strategy": "portfolio_allocator",
            "volatility_map": vol_map,
            "momentum_map": mom_map,
            "selected_symbol": best_symbol,
            "trade_decision": decision,
        }

