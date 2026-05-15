from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.trading import TradePosition, TradeRequest


class MT5Gateway(Protocol):
    def place_order(self, request: TradeRequest) -> TradePosition: ...
    def close_order(self, ticket: int) -> TradePosition | None: ...
    def list_open_positions(self) -> list[TradePosition]: ...
    def get_terminal_context(self) -> dict[str, str | list[str]]: ...


@dataclass
class InMemoryMT5Connector:
    """Placeholder connector that mimics MT5 behavior for local testing."""

    _positions: dict[int, TradePosition]
    _next_ticket: int = 1000

    def place_order(self, request: TradeRequest) -> TradePosition:
        ticket = self._next_ticket
        self._next_ticket += 1
        position = TradePosition(
            ticket=ticket,
            symbol=request.symbol,
            side=request.side,
            volume=request.volume,
            entry_price=1.0,
            current_price=1.0,
            pnl_percent=0.0,
            status="open",
        )
        self._positions[ticket] = position
        return position

    def close_order(self, ticket: int) -> TradePosition | None:
        position = self._positions.get(ticket)
        if position is None:
            return None
        closed = position.model_copy(update={"status": "closed"})
        self._positions.pop(ticket, None)
        return closed

    def list_open_positions(self) -> list[TradePosition]:
        return list(self._positions.values())

    def get_terminal_context(self) -> dict[str, str | list[str]]:
        return {
            "active_symbol": "EURUSD",
            "active_timeframe": "M15",
            "open_charts": ["EURUSD", "GBPUSD", "XAUUSD"],
        }


def build_mt5_connector() -> MT5Gateway:
    return InMemoryMT5Connector(_positions={})
