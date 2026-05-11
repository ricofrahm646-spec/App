"""Headless web research engine for market headline scanning."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from tools.search_tool import SearchTool


@dataclass(slots=True)
class WebScanResult:
    """Structured output from web scanning tasks."""

    ok: bool
    topic: str
    source: str
    headlines: list[dict[str, Any]]
    generated_at: str
    error: str | None = None


class WebEngine:
    """Collects market headlines using Playwright when available."""

    def __init__(self, workspace_root: str = ".") -> None:
        self.search_tool = SearchTool(workspace_root=workspace_root)

    async def scan_market_news(self, topic: str) -> WebScanResult:
        playwright_output = await self._scan_with_playwright(topic)
        if playwright_output is not None:
            return WebScanResult(
                ok=True,
                topic=topic,
                source="playwright",
                headlines=playwright_output,
                generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        fallback = await self.search_tool.web_search(f"{topic} market news", limit=8)
        return WebScanResult(
            ok=fallback.ok,
            topic=topic,
            source=fallback.source,
            headlines=fallback.items,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            error=None if fallback.ok else "fallback_search_failed",
        )

    async def _scan_with_playwright(self, topic: str) -> list[dict[str, Any]] | None:
        try:
            from playwright.async_api import async_playwright
        except Exception:
            return None

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            url = f"https://duckduckgo.com/?q={topic.replace(' ', '+')}+market+news"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(0.8)
                title_nodes = await page.query_selector_all("a[data-testid='result-title-a']")
                snippet_nodes = await page.query_selector_all("div[data-result='snippet']")
                items: list[dict[str, Any]] = []
                for idx, node in enumerate(title_nodes[:8]):
                    title = (await node.inner_text()).strip()
                    href = await node.get_attribute("href")
                    snippet = ""
                    if idx < len(snippet_nodes):
                        snippet = (await snippet_nodes[idx].inner_text()).strip()
                    items.append({"title": title, "snippet": snippet, "url": href or ""})
                return items
            finally:
                await context.close()
                await browser.close()

