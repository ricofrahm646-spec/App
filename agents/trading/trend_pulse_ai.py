"""Trend pulse agent using multi-horizon moving average momentum."""

from __future__ import annotations

from statistics import fmean
from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class TrendPulseAIAgent(BaseTradingAgent):
    """Identifies directional continuation based on trend-strength score."""

    keywords = ("trend", "momentum", "continuation", "pulse", "direction")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        closes = [item["close"] for item in rates[-150:]]
        fast = fmean(closes[-20:])
        medium = fmean(closes[-50:])
        slow = fmean(closes[-120:])
        trend_score = ((fast - medium) + (medium - slow)) / slow

        direction = "buy" if trend_score > 0.0012 else "sell" if trend_score < -0.0012 else ""
        confidence = 0.58 + min(0.3, abs(trend_score) * 150)
        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.02,
                sl_points=180,
                tp_points=310,
                comment="TrendPulseAI",
                confidence=min(confidence, 0.88),
            )
            if direction
            else None
        )
        return {
            "strategy": "trend_pulse_ai",
            "moving_averages": {"fast": fast, "medium": medium, "slow": slow},
            "trend_score": trend_score,
            "trade_decision": decision,
        }

