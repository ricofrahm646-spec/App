"""VisionOverlord agent for ultra-fast screen telemetry scans."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from typing import Any

from agents.base_agent import AgentResult, BaseAgent

try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None  # type: ignore[assignment]


class VisionOverlordAgent(BaseAgent):
    """Collects fast visual telemetry from the active desktop."""

    _KEYWORDS = {"vision", "screen", "chart", "apex", "scan", "screenshot"}

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(token in lowered for token in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        t0 = time.perf_counter()
        scan = await self._scan_screen()
        latency_ms = (time.perf_counter() - t0) * 1000
        output = {
            "task": task,
            "scan": scan,
            "latency_ms": round(latency_ms, 2),
            "note": "Visual telemetry only. No bypass or evasion behavior.",
        }
        await self.memory.store_knowledge(
            {"agent": self.name, "task": task, "scan": scan},
            tags=["system", "vision", "screen"],
        )
        return AgentResult(
            agent=self.name,
            status="success",
            output=output,
            metadata={"correlation_id": correlation_id, "latency_ms": round(latency_ms, 2)},
        )

    async def _scan_screen(self) -> dict[str, Any]:
        if pyautogui is None:
            return {
                "mode": "simulated",
                "reason": "pyautogui not available",
                "dominant_tones": [],
                "screen_size": None,
            }
        return await asyncio.to_thread(self._scan_screen_sync)

    def _scan_screen_sync(self) -> dict[str, Any]:
        screenshot = pyautogui.screenshot()
        width, height = screenshot.size
        points = []
        step_x = max(1, width // 40)
        step_y = max(1, height // 30)
        for y in range(0, height, step_y):
            for x in range(0, width, step_x):
                points.append(screenshot.getpixel((x, y)))
        dominant = Counter(self._quantize_color(pixel) for pixel in points).most_common(5)
        return {
            "mode": "live",
            "screen_size": {"width": width, "height": height},
            "sampled_points": len(points),
            "dominant_tones": [{"rgb": color, "count": count} for color, count in dominant],
        }

    def _quantize_color(self, pixel: tuple[int, int, int] | tuple[int, int, int, int]) -> tuple[int, int, int]:
        r, g, b = pixel[:3]
        return (r // 16 * 16, g // 16 * 16, b // 16 * 16)

