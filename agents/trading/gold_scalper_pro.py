"""Gold scalping agent using liquidity sweep and displacement logic."""

from __future__ import annotations

from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class GoldScalperProAgent(BaseTradingAgent):
    """Scalping logic inspired by SMC/ICT style liquidity concepts."""

    keywords = ("gold", "xauusd", "smc", "ict", "scalp", "liquidity")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        highs = [candle["high"] for candle in rates[-40:]]
        lows = [candle["low"] for candle in rates[-40:]]
        closes = [candle["close"] for candle in rates[-40:]]

        prev_high = max(highs[:-1])
        prev_low = min(lows[:-1])
        last = rates[-1]
        prior = rates[-2]

        sweep_high = last["high"] > prev_high and last["close"] < prev_high
        sweep_low = last["low"] < prev_low and last["close"] > prev_low
        displacement_up = (last["close"] - prior["close"]) > abs(prior["close"] - prior["open"]) * 1.2
        displacement_down = (prior["close"] - last["close"]) > abs(prior["close"] - prior["open"]) * 1.2

        direction = "buy" if sweep_low and displacement_up else "sell" if sweep_high and displacement_down else ""
        confidence = 0.74 if direction else 0.31
        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.02,
                sl_points=120,
                tp_points=180,
                comment="GoldScalperPro",
                confidence=confidence,
            )
            if direction
            else None
        )
        return {
            "strategy": "gold_scalper_pro",
            "liquidity_levels": {"prev_high": prev_high, "prev_low": prev_low},
            "signals": {
                "sweep_high": sweep_high,
                "sweep_low": sweep_low,
                "displacement_up": displacement_up,
                "displacement_down": displacement_down,
            },
            "recent_close_avg": sum(closes[-8:]) / 8,
            "trade_decision": decision,
        }

