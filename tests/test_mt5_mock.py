"""Mock MT5 connector smoke tests."""
from __future__ import annotations

import asyncio

from backend.app.schemas.common import TradeRequest
from mt5.mock_connector import MockMT5Connector


def test_open_and_close_cycle():
    conn = MockMT5Connector()
    req = TradeRequest(symbol="EURUSD", side="BUY", volume=0.1)
    view = asyncio.run(conn.open(req))
    assert view.status == "open"

    open_now = asyncio.run(conn.open_positions())
    assert len(open_now) == 1
    closed = asyncio.run(conn.close(view.ticket))  # type: ignore[arg-type]
    assert closed is not None
    assert closed.status == "closed"


def test_account_snapshot_consistent():
    conn = MockMT5Connector(starting_balance=5000.0)
    snap = asyncio.run(conn.account_snapshot())
    assert snap.balance == 5000.0
    assert snap.equity > 0
