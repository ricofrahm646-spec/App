"""Central memory store for tasks, events, results, and learned improvements."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class MemoryRecord:
    """Single memory entry tracked with metadata."""

    record_id: str
    category: str
    data: dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    )
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "category": self.category,
            "data": self.data,
            "created_at": self.created_at,
            "tags": self.tags,
        }


class MemoryStore:
    """Asynchronous, lock-safe in-memory data store with retrieval helpers."""

    def __init__(self) -> None:
        self._tasks: list[MemoryRecord] = []
        self._results: list[MemoryRecord] = []
        self._events: list[MemoryRecord] = []
        self._knowledge: list[MemoryRecord] = []
        self._improvements: list[MemoryRecord] = []
        self._profiles: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def store_task(self, task: dict[str, Any], tags: list[str] | None = None) -> str:
        return await self.store_record("task", task, tags=tags)

    async def store_result(self, result: dict[str, Any], tags: list[str] | None = None) -> str:
        return await self.store_record("result", result, tags=tags)

    async def store_event(self, event: dict[str, Any], tags: list[str] | None = None) -> str:
        return await self.store_record("event", event, tags=tags)

    async def store_knowledge(
        self, knowledge: dict[str, Any], tags: list[str] | None = None
    ) -> str:
        return await self.store_record("knowledge", knowledge, tags=tags)

    async def store_improvement(
        self, improvement: dict[str, Any], tags: list[str] | None = None
    ) -> str:
        return await self.store_record("improvement", improvement, tags=tags)

    async def store_record(
        self, category: str, data: dict[str, Any], tags: list[str] | None = None
    ) -> str:
        record = MemoryRecord(
            record_id=str(uuid4()),
            category=category,
            data=data,
            tags=tags or [],
        )
        async with self._lock:
            self._bucket_for(category).append(record)
        return record.record_id

    async def update_profile(self, profile_name: str, values: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            existing = self._profiles.get(profile_name, {})
            merged = {**existing, **values}
            self._profiles[profile_name] = merged
            return dict(merged)

    async def get_profile(self, profile_name: str) -> dict[str, Any]:
        async with self._lock:
            return dict(self._profiles.get(profile_name, {}))

    async def list_tasks(self) -> list[dict[str, Any]]:
        return await self._list_category("task")

    async def list_results(self) -> list[dict[str, Any]]:
        return await self._list_category("result")

    async def list_events(self) -> list[dict[str, Any]]:
        return await self._list_category("event")

    async def list_knowledge(self) -> list[dict[str, Any]]:
        return await self._list_category("knowledge")

    async def list_improvements(self) -> list[dict[str, Any]]:
        return await self._list_category("improvement")

    async def retrieve_relevant(
        self,
        query: str,
        *,
        categories: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []
        selected = categories or ["task", "result", "knowledge", "improvement", "event"]
        async with self._lock:
            candidates = [
                record
                for category in selected
                for record in self._bucket_for(category)
            ]
            ranked = sorted(
                candidates,
                key=lambda record: self._score_record(normalized_query, record),
                reverse=True,
            )[: max(limit, 1)]
        return [record.as_dict() for record in ranked if self._score_record(normalized_query, record) > 0.05]

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "tasks": [record.as_dict() for record in self._tasks],
                "results": [record.as_dict() for record in self._results],
                "events": [record.as_dict() for record in self._events],
                "knowledge": [record.as_dict() for record in self._knowledge],
                "improvements": [record.as_dict() for record in self._improvements],
                "profiles": dict(self._profiles),
            }

    async def _list_category(self, category: str) -> list[dict[str, Any]]:
        async with self._lock:
            return [record.as_dict() for record in self._bucket_for(category)]

    def _bucket_for(self, category: str) -> list[MemoryRecord]:
        if category == "task":
            return self._tasks
        if category == "result":
            return self._results
        if category == "event":
            return self._events
        if category == "knowledge":
            return self._knowledge
        if category == "improvement":
            return self._improvements
        raise ValueError(f"Unsupported memory category: {category}")

    def _score_record(self, query: str, record: MemoryRecord) -> float:
        blob = f"{record.category} {record.tags} {record.data}".lower()
        exact_bonus = 0.25 if query in blob else 0.0
        ratio = SequenceMatcher(None, query, blob).ratio()
        token_overlap = len(set(query.split()) & set(blob.split())) * 0.08
        return ratio + token_overlap + exact_bonus

