"""Main orchestration layer for JARVIS AI OS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from agents.base_agent import AgentResult, BaseAgent
from brain.planner import Planner
from core.event_bus import Event, EventBus
from memory.memory import MemoryStore


@dataclass(slots=True)
class OrchestratorResponse:
    """Structured response for orchestrator task execution."""

    task: str
    selected_agent: str
    planner_reasoning: str
    planner_confidence: float
    result: dict[str, Any]
    correlation_id: str


class Orchestrator:
    """Coordinates planning, routing, execution, and memory persistence."""

    def __init__(
        self,
        planner: Planner | None = None,
        event_bus: EventBus | None = None,
        memory: MemoryStore | None = None,
    ) -> None:
        self.planner = planner or Planner()
        self.event_bus = event_bus or EventBus()
        self.memory = memory or MemoryStore()
        self._agents: dict[str, BaseAgent] = {}
        self._events_wired = False

    async def setup(self) -> None:
        if self._events_wired:
            return
        await self.event_bus.subscribe_all(self._persist_event)
        self._events_wired = True

    async def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent
        await self.event_bus.publish(
            Event(
                event_type="agent.registered",
                source="Orchestrator",
                payload={"agent": agent.name},
            )
        )

    async def register_agents(self, agents: list[BaseAgent]) -> None:
        for agent in agents:
            await self.register_agent(agent)

    async def process_task(self, task: str) -> OrchestratorResponse:
        if not self._events_wired:
            await self.setup()

        correlation_id = str(uuid4())
        await self.memory.store_task({"task": task, "correlation_id": correlation_id})
        await self.event_bus.publish(
            Event(
                event_type="task.received",
                source="Orchestrator",
                correlation_id=correlation_id,
                payload={"task": task},
            )
        )

        decision = await self.planner.decide(task, self._agents.values())
        if not decision.agent_name or decision.agent_name not in self._agents:
            raise RuntimeError("No capable agent available to process task.")

        selected_agent = self._agents[decision.agent_name]
        await self.event_bus.publish(
            Event(
                event_type="task.routed",
                source="Orchestrator",
                correlation_id=correlation_id,
                payload={"task": task, "agent": selected_agent.name},
            )
        )

        result: AgentResult = await selected_agent.run(task, correlation_id=correlation_id)
        response = OrchestratorResponse(
            task=task,
            selected_agent=selected_agent.name,
            planner_reasoning=decision.reasoning,
            planner_confidence=decision.confidence,
            result={
                "status": result.status,
                "output": result.output,
                "metadata": result.metadata,
                "created_at": result.created_at,
            },
            correlation_id=correlation_id,
        )
        await self.memory.store_result(
            {
                "agent": "Orchestrator",
                "status": "success",
                "output": response.result,
                "metadata": {
                    "selected_agent": response.selected_agent,
                    "planner_confidence": response.planner_confidence,
                    "correlation_id": correlation_id,
                },
            }
        )
        return response

    async def _persist_event(self, event: Event) -> None:
        await self.memory.store_event(
            {
                "event_type": event.event_type,
                "source": event.source,
                "correlation_id": event.correlation_id,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
        )

