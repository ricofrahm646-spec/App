"""Web research agent with structured search and summarization."""

from __future__ import annotations

from collections import Counter
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from tools.search_tool import SearchTool


class WebResearchAgent(BaseAgent):
    """Performs internet research and summarizes key findings."""

    _KEYWORDS = {"web", "internet", "headline", "news", "research online", "search"}

    def __init__(self, *args: Any, search_tool: SearchTool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.search_tool = search_tool

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        query = task.replace("web", "").replace("internet", "").strip() or task
        response = await self.search_tool.web_search(query, limit=8)
        snippets = [item.get("snippet", "") for item in response.items if item.get("snippet")]
        keywords = self._extract_keywords(snippets)
        summary = self._build_summary(query, response.items, keywords)
        return AgentResult(
            agent=self.name,
            status="success",
            output={
                "query": query,
                "source": response.source,
                "items": response.items,
                "summary": summary,
                "top_keywords": keywords,
            },
            metadata={"correlation_id": correlation_id, "result_count": len(response.items)},
        )

    def _extract_keywords(self, snippets: list[str]) -> list[str]:
        stop = {"the", "and", "for", "with", "this", "that", "from", "into", "over", "are"}
        counter: Counter[str] = Counter()
        for snippet in snippets:
            for token in snippet.lower().split():
                token = token.strip(".,:;!?()[]{}\"'")
                if len(token) >= 4 and token not in stop:
                    counter[token] += 1
        return [item for item, _ in counter.most_common(6)]

    def _build_summary(
        self, query: str, items: list[dict[str, Any]], keywords: list[str]
    ) -> dict[str, Any]:
        highlights = []
        for item in items[:3]:
            snippet = item.get("snippet", "")
            if snippet:
                highlights.append(snippet[:240])
        return {
            "topic": query,
            "highlights": highlights,
            "insight": (
                "Signals suggest mixed conditions."
                if len(keywords) < 3
                else f"Dominant themes: {', '.join(keywords[:3])}."
            ),
        }

