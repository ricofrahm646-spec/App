"""High-level app-control interface for JARVIS command execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from core.safety import KillSwitch
from desktop.command_router import CommandRouter


@dataclass(slots=True)
class ControlResponse:
    """Response from controller command execution."""

    ok: bool
    command: str
    details: dict[str, Any]


class AppControlInterface:
    """Entry point for natural-language desktop automation commands."""

    def __init__(self, kill_switch: KillSwitch | None = None) -> None:
        self.kill_switch = kill_switch or KillSwitch()
        self.router = CommandRouter(kill_switch=self.kill_switch)

    async def execute(self, command: str) -> ControlResponse:
        lowered = command.strip().lower()
        if lowered in {"jarvis, abbruch", "jarvis abbruch", "abbruch", "abort", "stop"}:
            state = await self.kill_switch.activate(reason="manual_abort_command")
            return ControlResponse(
                ok=True,
                command=command,
                details={"kill_switch": asdict(state), "message": "Automation stopped immediately."},
            )
        if lowered in {"jarvis, weiter", "jarvis weiter", "resume", "fortsetzen"}:
            state = await self.kill_switch.reset(reason="manual_resume_command")
            return ControlResponse(
                ok=True,
                command=command,
                details={"kill_switch": asdict(state), "message": "Automation resumed."},
            )

        routed = await self.router.route(command)
        return ControlResponse(
            ok=routed.ok,
            command=command,
            details={
                "actions": routed.actions,
                "errors": routed.errors,
                "kill_switch": asdict(self.kill_switch.state),
            },
        )

