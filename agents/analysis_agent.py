"""Analysis-focused agent implementation."""

from __future__ import annotations

import asyncio
import statistics

from agents.base_agent import AgentResult, BaseAgent


class AnalysisAgent(BaseAgent):
    """Performs lightweight analytical reasoning on plain-text tasks."""

    _KEYWORDS = {
        "analyze",
        "analysis",
        "evaluate",
        "metrics",
        "score",
        "assess",
        "reason",
    }

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS) or len(task.split()) > 12

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        await asyncio.sleep(0)
        words = [word.strip(".,!?;:()[]{}") for word in task.split() if word.strip()]
        lengths = [len(word) for word in words]
        avg_len = statistics.fmean(lengths) if lengths else 0.0
        insights = [
            f"Token count: {len(words)}",
            f"Average token length: {avg_len:.2f}",
            f"Complexity rating: {self._complexity(len(words), avg_len)}",
        ]
        return AgentResult(
            agent=self.name,
            status="success",
            output={
                "summary": "Completed lexical and structural analysis of input task.",
                "metrics": {
                    "token_count": len(words),
                    "average_token_length": round(avg_len, 2),
                    "complexity": self._complexity(len(words), avg_len),
                },
                "insights": insights,
            },
            metadata={"correlation_id": correlation_id},
        )

    def _complexity(self, token_count: int, avg_len: float) -> str:
        if token_count > 40 or avg_len > 6:
            return "high"
        if token_count > 18 or avg_len > 4.5:
            return "medium"
        return "low"

