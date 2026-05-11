"""Volatility-aware agent controlling trade participation."""

from __future__ import annotations

from statistics import fmean
from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class VolatilityGuardianAgent(BaseTradingAgent):
    """Trades only when volatility is inside acceptable risk bands."""

    keywords = ("volatility", "atr", "risk-off", "guardian", "unstable")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candles = rates[-80:]
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
        atr = fmean(true_ranges[-14:])
        baseline = fmean(true_ranges)
        vol_ratio = atr / (baseline + 1e-9)

        trend = candles[-1]["close"] - candles[-12]["close"]
        direction = ""
        if 0.75 <= vol_ratio <= 1.6:
            direction = "buy" if trend > 0 else "sell"

        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.015 if vol_ratio > 1.3 else 0.025,
                sl_points=200,
                tp_points=260,
                comment="VolatilityGuardian",
                confidence=0.68,
            )
            if direction
            else None
        )

        return {
            "strategy": "volatility_guardian",
            "atr": atr,
            "baseline_tr": baseline,
            "volatility_ratio": vol_ratio,
            "trend": trend,
            "trade_decision": decision,
        }

