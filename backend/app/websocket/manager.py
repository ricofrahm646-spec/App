"""In-memory WebSocket fan-out for live dashboard metrics."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        logger.info("WS client connected (%s total)", len(self.active))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        data = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def metrics_broadcast_loop(mt5_snapshot_callable) -> None:
    """Background task: push periodic snapshots to dashboards."""
    while True:
        await asyncio.sleep(2.0)
        try:
            snap = mt5_snapshot_callable()
        except Exception as exc:  # pragma: no cover
            logger.exception("snapshot failed: %s", exc)
            snap = {"error": str(exc)}
        await manager.broadcast({"type": "metrics", "payload": snap})
