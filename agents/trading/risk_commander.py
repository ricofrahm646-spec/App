"""Risk commander agent with aggressive account growth sizing."""

from __future__ import annotations

from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class RiskCommanderAgent(BaseTradingAgent):
    """Applies adaptive risk sizing profile for account acceleration."""

    keywords = ("risk", "growth", "10€", "100€", "position size", "commander")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        account = await self.gateway.account_info()
        equity = 100.0
        if account.get("ok"):
            equity = float(account["account"].get("equity", equity))

        recent = rates[-15:]
        momentum = recent[-1]["close"] - recent[0]["close"]
        direction = "buy" if momentum > 0 else "sell"

        risk_pct = 0.04 if equity <= 150 else 0.03 if equity <= 400 else 0.02
        volume = max(0.01, min(2.0, round((equity * risk_pct) / 50, 2)))
        confidence = 0.63 + (0.08 if abs(momentum) > 0.002 * recent[-1]["close"] else 0.0)
        decision = TradeDecision(
            symbol=symbol,
            side=direction,
            volume=volume,
            sl_points=200,
            tp_points=420,
            comment="RiskCommander",
            confidence=min(confidence, 0.82),
        )
        return {
            "strategy": "risk_commander",
            "equity": equity,
            "risk_profile": {"risk_percent": risk_pct, "target_growth_mode": "aggressive"},
            "momentum": momentum,
            "trade_decision": decision,
        }

