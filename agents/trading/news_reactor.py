"""News-reactive trading agent using structured sentiment scoring."""

from __future__ import annotations

from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision
from tools.search_tool import SearchTool


class NewsReactorAgent(BaseTradingAgent):
    """Scans market headlines and blends sentiment with price direction."""

    keywords = ("news", "headline", "sentiment", "forex factory", "twitter", "x")

    def __init__(self, *args: Any, search_tool: SearchTool | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.search_tool = search_tool or SearchTool(workspace_root=".")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query = f"{symbol} forex market news"
        search = await self.search_tool.web_search(query, limit=6)
        headlines = [item.get("snippet", "") for item in search.items]
        sentiment = self._sentiment_score(headlines)
        price_momentum = rates[-1]["close"] - rates[-10]["close"]

        direction = ""
        if sentiment > 0.15 and price_momentum > 0:
            direction = "buy"
        elif sentiment < -0.15 and price_momentum < 0:
            direction = "sell"

        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.02,
                sl_points=160,
                tp_points=280,
                comment="NewsReactor",
                confidence=min(0.8, 0.55 + abs(sentiment)),
            )
            if direction
            else None
        )
        return {
            "strategy": "news_reactor",
            "query": query,
            "headline_count": len(headlines),
            "sentiment_score": round(sentiment, 4),
            "price_momentum": price_momentum,
            "headlines": headlines[:4],
            "trade_decision": decision,
        }

    def _sentiment_score(self, headlines: list[str]) -> float:
        if not headlines:
            return 0.0
        positive = {"bullish", "upside", "beat", "growth", "surge", "strength"}
        negative = {"bearish", "drop", "risk", "selloff", "weak", "decline"}
        score = 0.0
        for headline in headlines:
            words = set(headline.lower().split())
            score += len(words & positive) * 0.12
            score -= len(words & negative) * 0.12
        return score / max(len(headlines), 1)

