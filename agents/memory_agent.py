"""Memory retrieval agent for contextual continuity."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class MemoryAgent(BaseAgent):
    """Retrieves relevant historical context from memory store."""

    _KEYWORDS = {"remember", "recall", "context", "history", "previous", "memory"}

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        relevant = await self.memory.retrieve_relevant(task, limit=8)
        snapshot = await self.memory.snapshot()
        return AgentResult(
            agent=self.name,
            status="success",
            output={
                "query": task,
                "relevant_records": relevant,
                "memory_overview": {
                    "tasks": len(snapshot["tasks"]),
                    "results": len(snapshot["results"]),
                    "events": len(snapshot["events"]),
                    "knowledge": len(snapshot["knowledge"]),
                    "improvements": len(snapshot["improvements"]),
                },
            },
            metadata={"correlation_id": correlation_id, "match_count": len(relevant)},
        )

