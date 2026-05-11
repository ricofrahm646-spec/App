"""Routes parsed desktop intents into actionable operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from core.safety import KillSwitch
from desktop.app_controller import AppController
from desktop.input_controller import InputController
from desktop.intent_parser import IntentParser


@dataclass(slots=True)
class RoutedCommandResult:
    """Result of an entire routed desktop command sequence."""

    ok: bool
    command: str
    actions: list[dict[str, Any]]
    errors: list[str]


class CommandRouter:
    """Coordinates parsing and execution of desktop commands."""

    def __init__(
        self,
        parser: IntentParser | None = None,
        app_controller: AppController | None = None,
        input_controller: InputController | None = None,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        self.kill_switch = kill_switch or KillSwitch()
        self.parser = parser or IntentParser()
        self.app_controller = app_controller or AppController(kill_switch=self.kill_switch)
        self.input_controller = input_controller or InputController(kill_switch=self.kill_switch)

    async def route(self, command: str) -> RoutedCommandResult:
        parsed = self.parser.parse(command)
        execution_log: list[dict[str, Any]] = []
        errors: list[str] = []

        for action in parsed.actions:
            action_type = action.get("type")
            if action_type == "open_app":
                result = await self.app_controller.open_app(action.get("app", ""))
                execution_log.append({"action": action_type, "result": asdict(result)})
                if not result.ok and result.error:
                    errors.append(result.error)
            elif action_type == "close_app":
                result = await self.app_controller.close_app(action.get("app", ""))
                execution_log.append({"action": action_type, "result": asdict(result)})
                if not result.ok and result.error:
                    errors.append(result.error)
            elif action_type == "focus_app":
                # Best effort: opening a known app often focuses existing windows.
                result = await self.app_controller.open_app(action.get("app", ""))
                execution_log.append({"action": action_type, "result": asdict(result)})
                if not result.ok and result.error:
                    errors.append(result.error)
            elif action_type == "type_text":
                result = await self.input_controller.type_text(action.get("text", ""))
                execution_log.append({"action": action_type, "result": asdict(result)})
                if not result.ok and result.error:
                    errors.append(result.error)
            elif action_type == "press_key":
                result = await self.input_controller.press_key(action.get("key", "enter"))
                execution_log.append({"action": action_type, "result": asdict(result)})
                if not result.ok and result.error:
                    errors.append(result.error)
            elif action_type == "kill_switch":
                state = await self.kill_switch.activate(reason="voice_or_text_abort")
                execution_log.append(
                    {"action": action_type, "result": {"ok": True, "state": asdict(state)}}
                )
            else:
                execution_log.append(
                    {
                        "action": action_type,
                        "result": {"ok": True, "message": action.get("text", "")},
                    }
                )

        return RoutedCommandResult(
            ok=not errors,
            command=command,
            actions=execution_log,
            errors=errors,
        )

