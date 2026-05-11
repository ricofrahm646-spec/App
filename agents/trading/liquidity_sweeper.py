"""Liquidity sweeper agent detecting likely stop-hunt reversals."""

from __future__ import annotations

from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class LiquiditySweeperAgent(BaseTradingAgent):
    """Detects wick-based liquidity grabs and fade opportunities."""

    keywords = ("liquidity", "stop hunt", "sweep", "hunt", "wick")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candles = rates[-25:]
        recent_high = max(candle["high"] for candle in candles[:-1])
        recent_low = min(candle["low"] for candle in candles[:-1])
        last = candles[-1]
        body = abs(last["close"] - last["open"]) + 1e-8
        upper_wick = last["high"] - max(last["close"], last["open"])
        lower_wick = min(last["close"], last["open"]) - last["low"]

        bearish_stop_hunt = last["high"] > recent_high and upper_wick > body * 1.8
        bullish_stop_hunt = last["low"] < recent_low and lower_wick > body * 1.8

        direction = "sell" if bearish_stop_hunt else "buy" if bullish_stop_hunt else ""
        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.03,
                sl_points=170,
                tp_points=240,
                comment="LiquiditySweeper",
                confidence=0.7,
            )
            if direction
            else None
        )
        return {
            "strategy": "liquidity_sweeper",
            "recent_levels": {"high": recent_high, "low": recent_low},
            "wick_metrics": {"upper_wick": upper_wick, "lower_wick": lower_wick, "body": body},
            "stop_hunt": {"bearish": bearish_stop_hunt, "bullish": bullish_stop_hunt},
            "trade_decision": decision,
        }

