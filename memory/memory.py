"""Central memory store for tasks, events, and results."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class MemoryRecord:
    """Single memory entry tracked with metadata."""

    category: str
    data: dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    )


class MemoryStore:
    """Asynchronous, lock-safe in-memory data store."""

    def __init__(self) -> None:
        self._tasks: list[MemoryRecord] = []
        self._results: list[MemoryRecord] = []
        self._events: list[MemoryRecord] = []
        self._lock = asyncio.Lock()

    async def store_task(self, task: dict[str, Any]) -> None:
        async with self._lock:
            self._tasks.append(MemoryRecord(category="task", data=task))

    async def store_result(self, result: dict[str, Any]) -> None:
        async with self._lock:
            self._results.append(MemoryRecord(category="result", data=result))

    async def store_event(self, event: dict[str, Any]) -> None:
        async with self._lock:
            self._events.append(MemoryRecord(category="event", data=event))

    async def list_tasks(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [record.data for record in self._tasks]

    async def list_results(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [record.data for record in self._results]

    async def list_events(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [record.data for record in self._events]

    async def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        async with self._lock:
            return {
                "tasks": [record.data for record in self._tasks],
                "results": [record.data for record in self._results],
                "events": [record.data for record in self._events],
            }

