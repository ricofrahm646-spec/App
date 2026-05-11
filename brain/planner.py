"""Task planner that selects the best agent for incoming work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


class AgentDescriptor(Protocol):
    """Protocol for planner-compatible agents."""

    name: str

    async def can_handle(self, task: str) -> bool:
        """Whether the agent can handle a given task."""


@dataclass(slots=True)
class PlanDecision:
    """Planner output describing chosen routing decision."""

    agent_name: str
    confidence: float
    reasoning: str


class Planner:
    """Simple rule-based planner for multi-agent task routing."""

    def __init__(self) -> None:
        self._routing_rules: list[tuple[str, tuple[str, ...]]] = [
            ("ResearchAgent", ("research", "find", "discover", "lookup", "compare")),
            ("CodingAgent", ("code", "implement", "build", "bug", "refactor")),
            ("AnalysisAgent", ("analyze", "analysis", "evaluate", "assess", "explain")),
        ]

    async def decide(self, task: str, agents: Iterable[AgentDescriptor]) -> PlanDecision:
        normalized = task.lower()
        name_to_agent = {agent.name: agent for agent in agents}

        for agent_name, keywords in self._routing_rules:
            if any(keyword in normalized for keyword in keywords) and agent_name in name_to_agent:
                if await name_to_agent[agent_name].can_handle(task):
                    return PlanDecision(
                        agent_name=agent_name,
                        confidence=0.88,
                        reasoning=f"Matched routing keywords for {agent_name}.",
                    )

        for agent in agents:
            if await agent.can_handle(task):
                return PlanDecision(
                    agent_name=agent.name,
                    confidence=0.65,
                    reasoning=f"Fallback selected first capable agent: {agent.name}.",
                )

        return PlanDecision(
            agent_name="",
            confidence=0.0,
            reasoning="No capable agent found for task.",
        )

