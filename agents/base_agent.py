"""Base agent abstraction for all JARVIS AI OS agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from core.event_bus import Event, EventBus
from memory.memory import MemoryStore


@dataclass(slots=True)
class AgentResult:
    """Structured output from agent execution."""

    agent: str
    status: str
    output: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    )


class BaseAgent(ABC):
    """Shared behavior for async agents."""

    def __init__(self, event_bus: EventBus, memory: MemoryStore) -> None:
        self.event_bus = event_bus
        self.memory = memory
        self.name = self.__class__.__name__

    @abstractmethod
    async def can_handle(self, task: str) -> bool:
        """Return True when this agent can process the task."""

    @abstractmethod
    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        """Process the task and return a structured agent result."""

    async def run(self, task: str, correlation_id: str | None = None) -> AgentResult:
        correlation = correlation_id or str(uuid4())
        await self.event_bus.publish(
            Event(
                event_type="agent.started",
                source=self.name,
                correlation_id=correlation,
                payload={"task": task},
            )
        )

        try:
            result = await self.handle(task, correlation)
            await self.memory.store_result(
                {
                    "agent": self.name,
                    "status": result.status,
                    "output": result.output,
                    "metadata": result.metadata,
                    "created_at": result.created_at,
                    "correlation_id": correlation,
                }
            )
            await self.event_bus.publish(
                Event(
                    event_type="agent.completed",
                    source=self.name,
                    correlation_id=correlation,
                    payload={"result": result.output},
                )
            )
            return result
        except Exception as exc:
            error_result = AgentResult(
                agent=self.name,
                status="error",
                output={"error": str(exc)},
                metadata={"correlation_id": correlation},
            )
            await self.memory.store_result(
                {
                    "agent": self.name,
                    "status": error_result.status,
                    "output": error_result.output,
                    "metadata": error_result.metadata,
                    "created_at": error_result.created_at,
                    "correlation_id": correlation,
                }
            )
            await self.event_bus.publish(
                Event(
                    event_type="agent.failed",
                    source=self.name,
                    correlation_id=correlation,
                    payload={"error": str(exc)},
                )
            )
            return error_result

