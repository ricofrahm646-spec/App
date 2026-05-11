"""Shared base implementation for MT5-connected trading agents."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from agents.trading.mt5_gateway import MT5Gateway, TradeDecision
from core.event_bus import Event, EventBus
from memory.memory import MemoryStore


class BaseTradingAgent(BaseAgent):
    """Base class for trading-specialized agents using MT5 market data."""

    keywords: tuple[str, ...] = ()

    def __init__(
        self,
        event_bus: EventBus,
        memory: MemoryStore,
        gateway: MT5Gateway,
        *,
        symbol: str = "EURUSD",
        timeframe: str = "M5",
    ) -> None:
        super().__init__(event_bus, memory)
        self.gateway = gateway
        self.default_symbol = symbol
        self.default_timeframe = timeframe

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        has_keyword = any(keyword in lowered for keyword in self.keywords)
        has_trading_context = "trade" in lowered or "trading" in lowered
        has_symbol_hint = any(
            token in lowered for token in ("eurusd", "gbpusd", "usdjpy", "xauusd", "gold", "btcusd")
        )
        return has_keyword or (has_trading_context and has_symbol_hint)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        symbol = self._extract_symbol(task)
        rates_resp = await self.gateway.copy_rates(symbol=symbol, timeframe=self.default_timeframe, count=300)
        if not rates_resp.get("ok"):
            return AgentResult(
                agent=self.name,
                status="error",
                output={"error": "mt5_rates_failed", "details": rates_resp},
                metadata={"correlation_id": correlation_id, "symbol": symbol},
            )
        market_data = rates_resp["rates"]
        analysis = await self.analyze_market(task, symbol, market_data)

        trade_payload: dict[str, Any] | None = None
        decision: TradeDecision | None = analysis.get("trade_decision")
        if decision is not None:
            trade_payload = await self.gateway.send_order(decision)
            await self.event_bus.publish(
                Event(
                    event_type="trading.order.attempted",
                    source=self.name,
                    correlation_id=correlation_id,
                    payload={"symbol": decision.symbol, "side": decision.side, "response": trade_payload},
                )
            )

        output = {
            "symbol": symbol,
            "timeframe": self.default_timeframe,
            "analysis": analysis,
            "trade": trade_payload,
        }
        await self.memory.store_knowledge(
            {
                "agent": self.name,
                "symbol": symbol,
                "task": task,
                "analysis": analysis,
                "trade": trade_payload,
            },
            tags=["trading", symbol.lower(), self.name.lower()],
        )
        return AgentResult(
            agent=self.name,
            status="success",
            output=output,
            metadata={"correlation_id": correlation_id, "symbol": symbol},
        )

    @abstractmethod
    async def analyze_market(
        self,
        task: str,
        symbol: str,
        rates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run strategy-specific analytics and optional trade decision."""

    def _extract_symbol(self, task: str) -> str:
        tokens = task.upper().replace("/", " ").split()
        for token in tokens:
            if len(token) == 6 and token.isalpha():
                return token
            if token in {"XAUUSD", "BTCUSD", "ETHUSD", "US30", "NAS100"}:
                return token
        if "gold" in task.lower():
            return "XAUUSD"
        return self.default_symbol

