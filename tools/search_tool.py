"""Search utilities including web and local code search."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass(slots=True)
class SearchResult:
    """Structured search output."""

    ok: bool
    query: str
    source: str
    items: list[dict[str, Any]]
    metadata: dict[str, Any]


class SearchTool:
    """Provides local and lightweight web search capabilities."""

    def __init__(self, workspace_root: str) -> None:
        self.workspace = Path(workspace_root).resolve()

    async def web_search(self, query: str, limit: int = 5) -> SearchResult:
        url = (
            "https://duckduckgo.com/?q="
            f"{quote_plus(query)}&format=json&pretty=1&no_redirect=1&no_html=1"
        )

        def _fetch() -> dict[str, Any]:
            req = Request(
                url=url,
                headers={
                    "User-Agent": "JARVIS-AI-OS/1.0 (+local assistant)",
                    "Accept": "application/json",
                },
            )
            with urlopen(req, timeout=8) as response:
                raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)

        try:
            payload = await asyncio.to_thread(_fetch)
            related = payload.get("RelatedTopics", [])
            items: list[dict[str, Any]] = []
            for entry in related:
                if isinstance(entry, dict) and "Text" in entry:
                    items.append(
                        {
                            "title": entry.get("Text", "").split(" - ")[0],
                            "snippet": entry.get("Text", ""),
                            "url": entry.get("FirstURL", ""),
                        }
                    )
                if len(items) >= limit:
                    break
            return SearchResult(
                ok=True,
                query=query,
                source="duckduckgo",
                items=items,
                metadata={"fetched_items": len(items)},
            )
        except (URLError, TimeoutError, json.JSONDecodeError):
            fallback = self._offline_search(query, limit=limit)
            fallback.metadata["fallback_reason"] = "network_unavailable_or_invalid_payload"
            return fallback

    async def local_search(
        self,
        query: str,
        *,
        relative_path: str = ".",
        extensions: tuple[str, ...] = (".py", ".md", ".txt"),
        limit: int = 20,
    ) -> SearchResult:
        root = (self.workspace / relative_path).resolve()
        if self.workspace not in root.parents and root != self.workspace:
            raise ValueError("Path escapes workspace root")

        def _scan() -> list[dict[str, Any]]:
            pattern = re.compile(re.escape(query), flags=re.IGNORECASE)
            findings: list[dict[str, Any]] = []
            for file_path in root.rglob("*"):
                if not file_path.is_file() or file_path.suffix not in extensions:
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for index, line in enumerate(content.splitlines(), start=1):
                    if pattern.search(line):
                        findings.append(
                            {
                                "file": str(file_path.relative_to(self.workspace)),
                                "line": index,
                                "snippet": line.strip(),
                            }
                        )
                        if len(findings) >= limit:
                            return findings
            return findings

        items = await asyncio.to_thread(_scan)
        return SearchResult(
            ok=True,
            query=query,
            source="local",
            items=items,
            metadata={"matches": len(items), "relative_path": relative_path},
        )

    def _offline_search(self, query: str, limit: int) -> SearchResult:
        tokens = [token for token in re.split(r"\W+", query.lower()) if token]
        insights = [
            {
                "title": f"Topic signal: {token}",
                "snippet": f"Investigate '{token}' through official docs and benchmark reports.",
                "url": "",
            }
            for token in tokens[:limit]
        ] or [
            {
                "title": "General research guidance",
                "snippet": "Break down the request into scope, constraints, evidence, and trade-offs.",
                "url": "",
            }
        ]
        return SearchResult(
            ok=True,
            query=query,
            source="offline_heuristic",
            items=insights,
            metadata={"fetched_items": len(insights)},
        )

