"""Lightweight in-process pub/sub used for broadcasting events to WebSocket clients."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    def subscribe(self, topic: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._subscribers[topic].add(queue)
        return queue

    def unsubscribe(self, topic: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers[topic].discard(queue)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        message = {"topic": topic, "payload": payload}
        for queue in list(self._subscribers.get(topic, set())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass


bus = EventBus()
