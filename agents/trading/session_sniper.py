"""Session-aware breakout agent for major market opens."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.trading.base_trading_agent import BaseTradingAgent
from agents.trading.mt5_gateway import TradeDecision


class SessionSniperAgent(BaseTradingAgent):
    """Targets London/New York session volatility breakouts."""

    keywords = ("session", "london", "new york", "breakout", "sniper")

    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now_hour = datetime.now(timezone.utc).hour
        london_open = 7 <= now_hour <= 10
        ny_open = 12 <= now_hour <= 16
        session_active = london_open or ny_open

        window = rates[-25:]
        high = max(candle["high"] for candle in window[:-1])
        low = min(candle["low"] for candle in window[:-1])
        last = window[-1]
        breakout_up = last["close"] > high
        breakout_down = last["close"] < low

        direction = ""
        if session_active and breakout_up:
            direction = "buy"
        elif session_active and breakout_down:
            direction = "sell"

        decision = (
            TradeDecision(
                symbol=symbol,
                side=direction,
                volume=0.03,
                sl_points=130,
                tp_points=260,
                comment="SessionSniper",
                confidence=0.76,
            )
            if direction
            else None
        )
        return {
            "strategy": "session_sniper",
            "session_state": {
                "utc_hour": now_hour,
                "london_open": london_open,
                "new_york_open": ny_open,
                "active": session_active,
            },
            "range_levels": {"high": high, "low": low},
            "breakout": {"up": breakout_up, "down": breakout_down},
            "trade_decision": decision,
        }

