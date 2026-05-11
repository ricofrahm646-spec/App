"""Application launcher for desktop command execution."""

from __future__ import annotations

import asyncio
import platform
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any

from core.safety import KillSwitch


@dataclass(slots=True)
class AppCommandResult:
    """Result from app launch request."""

    ok: bool
    app: str
    command: str
    error: str | None
    metadata: dict[str, Any]


class AppController:
    """Starts whitelisted desktop applications in a cross-platform way."""

    def __init__(self, kill_switch: KillSwitch | None = None) -> None:
        self.kill_switch = kill_switch or KillSwitch()
        self._system = platform.system().lower()
        if self._system == "windows":
            self._commands = {
                "chrome": "start chrome",
                "notepad": "start notepad",
                "calculator": "start calc",
            }
            self._close = {
                "chrome": "taskkill /IM chrome.exe /F",
                "notepad": "taskkill /IM notepad.exe /F",
                "calculator": "taskkill /IM Calculator.exe /F",
            }
        elif self._system == "darwin":
            self._commands = {
                "chrome": "open -a 'Google Chrome'",
                "notepad": "open -a TextEdit",
                "calculator": "open -a Calculator",
            }
            self._close = {
                "chrome": "pkill -f 'Google Chrome'",
                "notepad": "pkill -f TextEdit",
                "calculator": "pkill -f Calculator",
            }
        else:
            self._commands = {
                "chrome": "google-chrome",
                "notepad": "gedit",
                "calculator": "gnome-calculator",
            }
            self._close = {
                "chrome": "pkill -f chrome",
                "notepad": "pkill -f gedit",
                "calculator": "pkill -f gnome-calculator",
            }

    async def open_app(self, app_name: str) -> AppCommandResult:
        if await self.kill_switch.is_active():
            return AppCommandResult(
                ok=False,
                app=app_name.strip().lower(),
                command="",
                error="Kill switch active",
                metadata={"blocked": True},
            )
        normalized = app_name.strip().lower()
        if normalized not in self._commands:
            return AppCommandResult(
                ok=False,
                app=normalized,
                command="",
                error=f"Unsupported app: {app_name}",
                metadata={"supported_apps": sorted(self._commands)},
            )
        command = self._commands[normalized]
        return await asyncio.to_thread(self._spawn, normalized, command)

    async def close_app(self, app_name: str) -> AppCommandResult:
        if await self.kill_switch.is_active():
            return AppCommandResult(
                ok=False,
                app=app_name.strip().lower(),
                command="",
                error="Kill switch active",
                metadata={"blocked": True},
            )
        normalized = app_name.strip().lower()
        if normalized not in self._close:
            return AppCommandResult(
                ok=False,
                app=normalized,
                command="",
                error=f"Unsupported app: {app_name}",
                metadata={"supported_apps": sorted(self._close)},
            )
        return await asyncio.to_thread(self._run_close, normalized, self._close[normalized])

    def _spawn(self, app: str, command: str) -> AppCommandResult:
        try:
            subprocess.Popen(shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return AppCommandResult(
                ok=True,
                app=app,
                command=command,
                error=None,
                metadata={"launched": True},
            )
        except Exception as exc:
            return AppCommandResult(
                ok=False,
                app=app,
                command=command,
                error=str(exc),
                metadata={"launched": False},
            )

    def _run_close(self, app: str, command: str) -> AppCommandResult:
        try:
            subprocess.run(shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return AppCommandResult(
                ok=True,
                app=app,
                command=command,
                error=None,
                metadata={"closed": True},
            )
        except Exception as exc:
            return AppCommandResult(
                ok=False,
                app=app,
                command=command,
                error=str(exc),
                metadata={"closed": False},
            )

