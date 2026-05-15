"""MetaTrader 5 connector with automatic mock fallback.

The real connector uses the official `MetaTrader5` Python package (Windows-only).
On Linux/macOS — or when `MT5_MOCK=true` — the mock connector is used so the
rest of the platform works end-to-end. The interface is identical so swapping
between real / mock is transparent.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger
from backend.app.schemas.common import AccountSnapshot, TradeRequest, TradeView


class MT5Protocol(Protocol):
    async def is_connected(self) -> bool: ...
    async def account_snapshot(self) -> AccountSnapshot: ...
    async def symbols(self) -> list[str]: ...
    async def open(self, req: TradeRequest) -> TradeView: ...
    async def close(self, ticket: int) -> TradeView | None: ...
    async def close_all(self) -> int: ...
    async def open_positions(self) -> list[TradeView]: ...
    async def history(self, limit: int = 50) -> list[TradeView]: ...
    async def modify(self, ticket: int, sl: float | None = None, tp: float | None = None) -> bool: ...
    async def price(self, symbol: str) -> float: ...


@lru_cache(maxsize=1)
def get_connector() -> MT5Protocol:
    """Return the active MT5 connector (real or mock)."""
    if not settings.mt5_mock:
        try:
            from mt5.live_connector import LiveMT5Connector

            connector = LiveMT5Connector()
            logger.info("Using LIVE MetaTrader 5 connector")
            return connector
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falling back to mock MT5 connector ({})", exc)

    from mt5.mock_connector import MockMT5Connector

    logger.info("Using MOCK MetaTrader 5 connector")
    return MockMT5Connector()
