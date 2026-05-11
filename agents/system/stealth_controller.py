"""StealthController agent for smooth autonomous app control."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from controller import AppControlInterface
from desktop.input_controller import InputController


class StealthControllerAgent(BaseAgent):
    """Executes smooth desktop actions through app control + bezier paths."""

    _KEYWORDS = {"control", "app", "open", "close", "type", "press", "mouse", "apex", "mt5"}

    def __init__(
        self,
        *args: Any,
        controller: AppControlInterface,
        input_controller: InputController | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.controller = controller
        self.input_controller = input_controller or controller.router.input_controller

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        commands = self._extract_commands(task)
        executed: list[dict[str, Any]] = []

        for command in commands:
            if command["type"] == "move_mouse":
                path = self._build_bezier_path(0, 0, command["x"], command["y"], steps=18)
                step_results = []
                for point in path:
                    result = await self.input_controller.move_mouse(point["x"], point["y"])
                    step_results.append({"point": point, "ok": result.ok, "error": result.error})
                    if not result.ok:
                        break
                executed.append({"command": command, "result": step_results})
                continue

            response = await self.controller.execute(command["raw"])
            executed.append({"command": command, "result": asdict(response)})

        await self.memory.store_knowledge(
            {"agent": self.name, "task": task, "commands": commands, "executed": executed},
            tags=["system", "control", "automation"],
        )
        return AgentResult(
            agent=self.name,
            status="success",
            output={"task": task, "commands": commands, "executed": executed},
            metadata={"correlation_id": correlation_id, "command_count": len(commands)},
        )

    def _extract_commands(self, task: str) -> list[dict[str, Any]]:
        lowered = task.lower().strip()
        command_chunks = [chunk.strip() for chunk in lowered.replace("jarvis,", "").split(" and ") if chunk.strip()]
        commands: list[dict[str, Any]] = []
        for chunk in command_chunks:
            if chunk.startswith("move mouse to "):
                payload = chunk.replace("move mouse to ", "", 1)
                try:
                    x_val, y_val = payload.split(maxsplit=1)
                    commands.append(
                        {
                            "type": "move_mouse",
                            "x": int(float(x_val)),
                            "y": int(float(y_val)),
                            "raw": chunk,
                        }
                    )
                    continue
                except Exception:
                    pass
            commands.append({"type": "app_control", "raw": chunk})
        return commands

    def _build_bezier_path(self, x0: int, y0: int, x3: int, y3: int, *, steps: int) -> list[dict[str, int]]:
        x1 = int(x0 + (x3 - x0) * 0.28)
        y1 = int(y0 + (y3 - y0) * 0.10)
        x2 = int(x0 + (x3 - x0) * 0.72)
        y2 = int(y0 + (y3 - y0) * 0.90)
        path: list[dict[str, int]] = []
        for step in range(1, steps + 1):
            t = step / steps
            x = int(((1 - t) ** 3 * x0) + (3 * ((1 - t) ** 2) * t * x1) + (3 * (1 - t) * (t**2) * x2) + ((t**3) * x3))
            y = int(((1 - t) ** 3 * y0) + (3 * ((1 - t) ** 2) * t * y1) + (3 * (1 - t) * (t**2) * y2) + ((t**3) * y3))
            path.append({"x": x, "y": y})
        return path

