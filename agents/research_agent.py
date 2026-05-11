"""Research-focused agent implementation."""

from __future__ import annotations

import asyncio
import re

from agents.base_agent import AgentResult, BaseAgent


class ResearchAgent(BaseAgent):
    """Performs structured research synthesis from task prompts."""

    _KEYWORDS = {
        "research",
        "find",
        "discover",
        "lookup",
        "investigate",
        "compare",
        "market",
        "trend",
    }

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        await asyncio.sleep(0)
        entities = self._extract_entities(task)
        key_points = self._build_key_points(task, entities)
        sources = self._generate_source_hints(entities)
        summary = (
            f"Research summary for '{task}': identified {len(entities)} focus area(s) "
            f"and generated {len(key_points)} actionable insights."
        )
        return AgentResult(
            agent=self.name,
            status="success",
            output={
                "summary": summary,
                "focus_areas": entities,
                "key_points": key_points,
                "suggested_sources": sources,
            },
            metadata={"correlation_id": correlation_id, "insight_count": len(key_points)},
        )

    def _extract_entities(self, task: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\+_\.]{2,}", task)
        stop_words = {"the", "and", "with", "about", "that", "from", "this"}
        entities = [token for token in tokens if token.lower() not in stop_words]
        return entities[:5] or ["general topic"]

    def _build_key_points(self, task: str, entities: list[str]) -> list[str]:
        points = [
            f"Define measurable objective for {entities[0]}.",
            f"Collect baseline data relevant to '{task}'.",
            "Cross-check assumptions across at least two independent sources.",
        ]
        if len(entities) > 1:
            points.append(f"Compare {entities[0]} against {entities[1]} for trade-off analysis.")
        return points

    def _generate_source_hints(self, entities: list[str]) -> list[dict[str, str]]:
        source_types = ["official_docs", "industry_report", "technical_blog", "community_discussion"]
        return [
            {
                "query": f"{entity} {source_type.replace('_', ' ')}",
                "source_type": source_type,
            }
            for entity in entities[:2]
            for source_type in source_types[:2]
        ]

