"""Risk engine rule tests."""
from __future__ import annotations

import asyncio

import pytest

from backend.app.core.config import settings
from backend.app.schemas.common import TradeRequest
from mt5 import connector as connector_module
from mt5.mock_connector import MockMT5Connector
from risk_management.engine import RiskEngine


@pytest.fixture
def patched_connector(monkeypatch: pytest.MonkeyPatch) -> MockMT5Connector:
    conn = MockMT5Connector()
    monkeypatch.setattr(connector_module, "get_connector", lambda: conn)
    return conn


def test_blocks_opposite_side(patched_connector: MockMT5Connector) -> None:
    asyncio.run(patched_connector.open(TradeRequest(symbol="EURUSD", side="BUY", volume=0.1)))
    engine = RiskEngine()
    ok, reason = asyncio.run(
        engine.allow_new_trade(TradeRequest(symbol="EURUSD", side="SELL", volume=0.1))
    )
    assert not ok
    assert "opposite" in reason or "max" in reason


def test_blocks_max_open_trades(patched_connector: MockMT5Connector) -> None:
    asyncio.run(patched_connector.open(TradeRequest(symbol="EURUSD", side="BUY", volume=0.1)))
    engine = RiskEngine()
    ok, reason = asyncio.run(
        engine.allow_new_trade(TradeRequest(symbol="GBPUSD", side="BUY", volume=0.1))
    )
    if settings.risk_max_open_trades <= 1:
        assert not ok
        assert "max" in reason
