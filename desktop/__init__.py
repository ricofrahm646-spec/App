"""Desktop automation package for JARVIS AI OS."""

from desktop.app_controller import AppController, AppCommandResult
from desktop.command_router import CommandRouter, RoutedCommandResult
from desktop.input_controller import InputActionResult, InputController
from desktop.intent_parser import IntentParser, ParsedIntent

__all__ = [
    "AppController",
    "AppCommandResult",
    "CommandRouter",
    "RoutedCommandResult",
    "InputController",
    "InputActionResult",
    "IntentParser",
    "ParsedIntent",
]

