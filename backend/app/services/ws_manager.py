"""WebSocket connection manager — fan-out broadcaster."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from backend.app.core.logging_setup import logger


class WebSocketManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("WS client connected ({} active)", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        logger.info("WS client disconnected ({} active)", len(self._clients))

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        data = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for client in list(self._clients):
            try:
                await client.send_text(data)
            except Exception:  # noqa: BLE001
                dead.append(client)
        if dead:
            async with self._lock:
                for c in dead:
                    self._clients.discard(c)


manager = WebSocketManager()
