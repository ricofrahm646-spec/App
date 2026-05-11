"""Task planner agent for decomposing complex objectives."""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent


class TaskPlannerAgent(BaseAgent):
    """Breaks down goals into sequenced subtasks with dependencies."""

    _KEYWORDS = {"plan", "roadmap", "break down", "milestone", "subtask", "strategy"}

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        objective = task.strip()
        chunks = self._infer_workstreams(objective)
        subtasks = []
        for index, chunk in enumerate(chunks, start=1):
            subtasks.append(
                {
                    "id": f"S{index:02d}",
                    "title": chunk["title"],
                    "description": chunk["description"],
                    "depends_on": [f"S{index-1:02d}"] if index > 1 else [],
                    "estimated_complexity": chunk["complexity"],
                }
            )
        return AgentResult(
            agent=self.name,
            status="success",
            output={
                "objective": objective,
                "subtasks": subtasks,
                "execution_order": [item["id"] for item in subtasks],
                "risk_flags": self._risk_flags(objective),
            },
            metadata={"correlation_id": correlation_id, "subtask_count": len(subtasks)},
        )

    def _infer_workstreams(self, objective: str) -> list[dict[str, str]]:
        base = [
            {
                "title": "Requirement decomposition",
                "description": f"Extract constraints and acceptance criteria from: {objective}",
                "complexity": "medium",
            },
            {
                "title": "System design",
                "description": "Define architecture modules, data flow, and integration boundaries.",
                "complexity": "high",
            },
            {
                "title": "Implementation",
                "description": "Develop components incrementally with interface contracts.",
                "complexity": "high",
            },
            {
                "title": "Validation and hardening",
                "description": "Run tests, benchmark, and add operational safeguards.",
                "complexity": "medium",
            },
        ]
        if "trading" in objective.lower():
            base.insert(
                2,
                {
                    "title": "Market strategy logic",
                    "description": "Implement strategy, risk management, and scenario simulation.",
                    "complexity": "high",
                },
            )
        return base

    def _risk_flags(self, objective: str) -> list[str]:
        flags: list[str] = []
        lowered = objective.lower()
        if "real money" in lowered or "live trade" in lowered:
            flags.append("Enable strict risk and kill-switch controls for live execution.")
        if "desktop control" in lowered:
            flags.append("Validate commands and maintain explicit human override.")
        return flags

