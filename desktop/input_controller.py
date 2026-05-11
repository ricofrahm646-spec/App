"""Keyboard and mouse input abstraction for desktop automation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from core.safety import KillSwitch

try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency fallback
    pyautogui = None  # type: ignore[assignment]


@dataclass(slots=True)
class InputActionResult:
    """Result from keyboard/mouse action."""

    ok: bool
    action: str
    metadata: dict[str, Any]
    error: str | None


class InputController:
    """Executes keyboard and mouse actions via PyAutoGUI when available."""

    def __init__(self, kill_switch: KillSwitch | None = None) -> None:
        self._enabled = pyautogui is not None
        self.kill_switch = kill_switch or KillSwitch()

    async def type_text(self, text: str) -> InputActionResult:
        if await self.kill_switch.is_active():
            return InputActionResult(
                ok=False,
                action="type_text",
                metadata={"blocked": True, "text": text},
                error="Kill switch active",
            )
        if not self._enabled:
            return InputActionResult(
                ok=True,
                action="type_text",
                metadata={"simulated": True, "text": text},
                error=None,
            )
        return await asyncio.to_thread(self._type_text_sync, text)

    async def press_key(self, key: str) -> InputActionResult:
        if await self.kill_switch.is_active():
            return InputActionResult(
                ok=False,
                action="press_key",
                metadata={"blocked": True, "key": key},
                error="Kill switch active",
            )
        if not self._enabled:
            return InputActionResult(
                ok=True,
                action="press_key",
                metadata={"simulated": True, "key": key},
                error=None,
            )
        return await asyncio.to_thread(self._press_key_sync, key)

    async def move_mouse(self, x: int, y: int) -> InputActionResult:
        if await self.kill_switch.is_active():
            return InputActionResult(
                ok=False,
                action="move_mouse",
                metadata={"blocked": True, "x": x, "y": y},
                error="Kill switch active",
            )
        if not self._enabled:
            return InputActionResult(
                ok=True,
                action="move_mouse",
                metadata={"simulated": True, "x": x, "y": y},
                error=None,
            )
        return await asyncio.to_thread(self._move_mouse_sync, x, y)

    def _type_text_sync(self, text: str) -> InputActionResult:
        try:
            pyautogui.write(text)
            return InputActionResult(ok=True, action="type_text", metadata={"text": text}, error=None)
        except Exception as exc:
            return InputActionResult(
                ok=False,
                action="type_text",
                metadata={"text": text},
                error=str(exc),
            )

    def _press_key_sync(self, key: str) -> InputActionResult:
        try:
            pyautogui.press(key)
            return InputActionResult(ok=True, action="press_key", metadata={"key": key}, error=None)
        except Exception as exc:
            return InputActionResult(ok=False, action="press_key", metadata={"key": key}, error=str(exc))

    def _move_mouse_sync(self, x: int, y: int) -> InputActionResult:
        try:
            pyautogui.moveTo(x, y)
            return InputActionResult(
                ok=True,
                action="move_mouse",
                metadata={"x": x, "y": y},
                error=None,
            )
        except Exception as exc:
            return InputActionResult(
                ok=False,
                action="move_mouse",
                metadata={"x": x, "y": y},
                error=str(exc),
            )

