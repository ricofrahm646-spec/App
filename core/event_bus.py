"""Asynchronous event bus for decoupled agent communication."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, DefaultDict
from uuid import uuid4

LOGGER = logging.getLogger(__name__)

EventHandler = Callable[["Event"], Awaitable[None] | None]


@dataclass(slots=True)
class Event:
    """Represents an event flowing through the system."""

    event_type: str
    source: str
    payload: dict[str, Any]
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    )


class EventBus:
    """In-memory asynchronous event pub/sub implementation."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, list[EventHandler]] = defaultdict(list)
        self._global_subscribers: list[EventHandler] = []
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to a specific event type."""
        async with self._lock:
            self._subscribers[event_type].append(handler)

    async def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all event types."""
        async with self._lock:
            self._global_subscribers.append(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers."""
        async with self._lock:
            targeted = list(self._subscribers.get(event.event_type, []))
            global_handlers = list(self._global_subscribers)

        if not targeted and not global_handlers:
            return

        await asyncio.gather(
            *(self._invoke_handler(handler, event) for handler in (*targeted, *global_handlers))
        )

    async def _invoke_handler(self, handler: EventHandler, event: Event) -> None:
        try:
            maybe_awaitable = handler(event)
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception(
                "Event handler failed for %s from %s: %s",
                event.event_type,
                event.source,
                exc,
            )

