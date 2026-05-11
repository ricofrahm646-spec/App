"""GhostBrowser agent for background web intelligence collection."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from web_engine import WebEngine


class GhostBrowserAgent(BaseAgent):
    """Uses headless browser research to gather structured web intelligence."""

    _KEYWORDS = {"browser", "web", "headline", "news", "scan", "twitter", "forexfactory"}

    def __init__(self, *args: Any, web_engine: WebEngine, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.web_engine = web_engine

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        topic = self._extract_topic(task)
        scan = await self.web_engine.scan_market_news(topic)
        sentiment = self._score_sentiment(scan.headlines)
        output = {
            "topic": topic,
            "scan": asdict(scan),
            "sentiment": sentiment,
            "note": "Headless research only; no anti-detection/evasion mechanisms.",
        }
        await self.memory.store_knowledge(
            {"agent": self.name, "task": task, "topic": topic, "sentiment": sentiment},
            tags=["system", "web", "sentiment"],
        )
        return AgentResult(
            agent=self.name,
            status="success" if scan.ok else "error",
            output=output,
            metadata={"correlation_id": correlation_id, "headline_count": len(scan.headlines)},
        )

    def _extract_topic(self, task: str) -> str:
        cleaned = task.lower().replace("scan", "").replace("news", "").replace("browser", "").strip()
        cleaned = " ".join(cleaned.split())
        return cleaned or "forex market"

    def _score_sentiment(self, headlines: list[dict[str, Any]]) -> dict[str, Any]:
        positive = {"bullish", "surge", "gain", "optimism", "upside", "beat"}
        negative = {"bearish", "drop", "risk", "decline", "weak", "selloff"}
        score = 0.0
        for item in headlines:
            text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
            words = set(text.split())
            score += len(words & positive) * 0.15
            score -= len(words & negative) * 0.15
        label = "neutral"
        if score > 0.4:
            label = "positive"
        elif score < -0.4:
            label = "negative"
        return {"score": round(score, 4), "label": label}

