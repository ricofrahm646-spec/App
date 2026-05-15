import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect, status

from app.core.logging import logger


class ConnectionInfo:
    """Holds metadata for a single WebSocket connection."""

    def __init__(self, websocket: WebSocket, client_id: str, user_id: Optional[int] = None):
        self.websocket = websocket
        self.client_id = client_id
        self.user_id = user_id
        self.connected_at: datetime = datetime.now(timezone.utc)
        self.subscriptions: Set[str] = set()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ConnectionInfo client_id={self.client_id} user_id={self.user_id}>"


class WebSocketManager:
    """Manages all active WebSocket connections for the application.

    Features:
    - Per-client connection tracking with optional user binding.
    - Topic-based subscriptions so clients receive only relevant events.
    - Graceful disconnect handling.
    - Broadcast and personal message delivery.
    """

    def __init__(self) -> None:
        # client_id -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # topic -> set of client_ids
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[int] = None,
    ) -> ConnectionInfo:
        """Accept the WebSocket handshake and register the connection."""
        await websocket.accept()
        info = ConnectionInfo(websocket, client_id, user_id)

        async with self._lock:
            self._connections[client_id] = info

        logger.info(f"WebSocket connected: client_id={client_id} user_id={user_id}")

        await self.send_personal_message(
            client_id,
            {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return info

    async def disconnect(self, client_id: str) -> None:
        """Remove a connection and clean up all its subscriptions."""
        async with self._lock:
            info = self._connections.pop(client_id, None)
            if info is None:
                return
            for topic in list(info.subscriptions):
                self._subscriptions[topic].discard(client_id)
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]

        logger.info(f"WebSocket disconnected: client_id={client_id}")

    # ── Subscriptions ──────────────────────────────────────────────────────────

    async def subscribe(self, client_id: str, topic: str) -> None:
        """Subscribe a client to a named topic (e.g. 'trades', 'EURUSD')."""
        async with self._lock:
            info = self._connections.get(client_id)
            if info is None:
                return
            info.subscriptions.add(topic)
            self._subscriptions[topic].add(client_id)
        logger.debug(f"Client {client_id} subscribed to topic '{topic}'")

    async def unsubscribe(self, client_id: str, topic: str) -> None:
        """Unsubscribe a client from a named topic."""
        async with self._lock:
            info = self._connections.get(client_id)
            if info:
                info.subscriptions.discard(topic)
            self._subscriptions[topic].discard(client_id)
        logger.debug(f"Client {client_id} unsubscribed from topic '{topic}'")

    # ── Messaging ──────────────────────────────────────────────────────────────

    async def send_personal_message(
        self, client_id: str, data: Any
    ) -> bool:
        """Send a message to a single client identified by client_id.

        Returns True if delivered, False if the client was not found or send failed.
        """
        info = self._connections.get(client_id)
        if info is None:
            return False

        payload = data if isinstance(data, str) else json.dumps(data, default=str)
        try:
            await info.websocket.send_text(payload)
            return True
        except (WebSocketDisconnect, RuntimeError) as exc:
            logger.warning(f"Failed to send to {client_id}: {exc}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, data: Any, topic: Optional[str] = None) -> int:
        """Broadcast a message to all connected clients or to topic subscribers.

        Args:
            data: JSON-serialisable dict or raw string.
            topic: If provided, only clients subscribed to this topic receive the message.

        Returns:
            Number of clients that successfully received the message.
        """
        payload = data if isinstance(data, str) else json.dumps(data, default=str)

        if topic is not None:
            target_ids = list(self._subscriptions.get(topic, set()))
        else:
            target_ids = list(self._connections.keys())

        if not target_ids:
            return 0

        results = await asyncio.gather(
            *[self.send_personal_message(cid, payload) for cid in target_ids],
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    async def broadcast_to_user(self, user_id: int, data: Any) -> int:
        """Broadcast a message to all connections belonging to a specific user."""
        target_ids = [
            cid
            for cid, info in self._connections.items()
            if info.user_id == user_id
        ]
        if not target_ids:
            return 0

        payload = data if isinstance(data, str) else json.dumps(data, default=str)
        results = await asyncio.gather(
            *[self.send_personal_message(cid, payload) for cid in target_ids],
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    # ── Inspection ─────────────────────────────────────────────────────────────

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    def get_connection_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "client_id": info.client_id,
                "user_id": info.user_id,
                "connected_at": info.connected_at.isoformat(),
                "subscriptions": list(info.subscriptions),
            }
            for info in self._connections.values()
        ]

    async def handle_client_message(self, client_id: str, raw: str) -> None:
        """Parse and act on an incoming message from a client.

        Supported message types:
        - {"type": "subscribe", "topic": "<topic>"}
        - {"type": "unsubscribe", "topic": "<topic>"}
        - {"type": "ping"}
        """
        try:
            message: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            await self.send_personal_message(
                client_id, {"type": "error", "detail": "Invalid JSON"}
            )
            return

        msg_type = message.get("type", "")

        if msg_type == "subscribe":
            topic = message.get("topic", "")
            if topic:
                await self.subscribe(client_id, topic)
                await self.send_personal_message(
                    client_id, {"type": "subscribed", "topic": topic}
                )

        elif msg_type == "unsubscribe":
            topic = message.get("topic", "")
            if topic:
                await self.unsubscribe(client_id, topic)
                await self.send_personal_message(
                    client_id, {"type": "unsubscribed", "topic": topic}
                )

        elif msg_type == "ping":
            await self.send_personal_message(
                client_id,
                {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()},
            )

        else:
            await self.send_personal_message(
                client_id, {"type": "error", "detail": f"Unknown message type: {msg_type}"}
            )


# Singleton instance shared across the application
ws_manager = WebSocketManager()
