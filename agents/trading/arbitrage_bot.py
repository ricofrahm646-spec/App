"""Statistical arbitrage agent across correlated FX symbols."""

from __future__ import annotations

from statistics import fmean
from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class ArbitrageBotAgent(BaseTradingAgent):
    """Uses spread divergence between correlated pairs for mean reversion."""

    keywords = ("arbitrage", "pair spread", "divergence", "correlation")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        hedge_symbol = "GBPUSD" if symbol != "GBPUSD" else "EURUSD"
        hedge_resp = await self.gateway.copy_rates(hedge_symbol, timeframe=self.default_timeframe, count=300)
        if not hedge_resp.get("ok"):
            return {
                "strategy": "arbitrage_bot",
                "error": "hedge_symbol_fetch_failed",
                "details": hedge_resp,
                "trade_decision": None,
            }

        base_closes = [candle["close"] for candle in rates[-120:]]
        hedge_closes = [candle["close"] for candle in hedge_resp["rates"][-120:]]
        base_norm = [value / base_closes[0] for value in base_closes]
        hedge_norm = [value / hedge_closes[0] for value in hedge_closes]
        spread_series = [base_norm[i] - hedge_norm[i] for i in range(min(len(base_norm), len(hedge_norm)))]
        current_spread = spread_series[-1]
        mean_spread = fmean(spread_series)
        std_proxy = max(1e-8, fmean(abs(item - mean_spread) for item in spread_series))
        z_score = (current_spread - mean_spread) / std_proxy

        direction = "sell" if z_score > 1.2 else "buy" if z_score < -1.2 else ""
        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.02,
                sl_points=180,
                tp_points=220,
                comment="ArbitrageBot",
                confidence=min(0.79, 0.57 + min(abs(z_score), 2.0) * 0.1),
            )
            if direction
            else None
        )

        return {
            "strategy": "arbitrage_bot",
            "base_symbol": symbol,
            "hedge_symbol": hedge_symbol,
            "z_score": round(z_score, 4),
            "current_spread": current_spread,
            "mean_spread": mean_spread,
            "trade_decision": decision,
        }

