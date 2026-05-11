"""Orderflow-focused trading agent using tick-volume imbalance."""

from __future__ import annotations

from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class OrderflowMasterAgent(BaseTradingAgent):
    """Detects directional pressure through volume and candle body bias."""

    keywords = ("orderflow", "flow", "volume imbalance", "delta", "footprint")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candles = rates[-60:]
        bullish_pressure = 0.0
        bearish_pressure = 0.0
        for candle in candles:
            volume = float(candle.get("tick_volume", 0) or 0)
            body = candle["close"] - candle["open"]
            if body >= 0:
                bullish_pressure += volume * (abs(body) + 1e-8)
            else:
                bearish_pressure += volume * (abs(body) + 1e-8)

        imbalance = (bullish_pressure - bearish_pressure) / (bullish_pressure + bearish_pressure + 1e-9)
        direction = "buy" if imbalance > 0.12 else "sell" if imbalance < -0.12 else ""

        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.025,
                sl_points=140,
                tp_points=250,
                comment="OrderflowMaster",
                confidence=min(0.84, 0.6 + abs(imbalance)),
            )
            if direction
            else None
        )

        return {
            "strategy": "orderflow_master",
            "bullish_pressure": bullish_pressure,
            "bearish_pressure": bearish_pressure,
            "imbalance": round(imbalance, 6),
            "trade_decision": decision,
        }

