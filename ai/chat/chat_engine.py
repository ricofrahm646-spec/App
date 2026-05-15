"""
JARVIS AI Trading OS - Chat Engine

Processes natural language commands (German and English) and maps them
to system actions such as creating bots, optimizing strategies, etc.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional

from ai.chat.code_generator import CodeGenerator, GeneratedFile

logger = logging.getLogger(__name__)


class CommandIntent(Enum):
    CREATE_BOT = auto()
    OPTIMIZE_STRATEGY = auto()
    CREATE_NEWS_FILTER = auto()
    CREATE_INDICATOR = auto()
    OPTIMIZE_WINRATE = auto()
    CREATE_TELEGRAM_BOT = auto()
    ADD_TRAILING_STOP = auto()
    OPTIMIZE_DRAWDOWN = auto()
    UNKNOWN = auto()


@dataclass
class ChatCommand:
    raw_text: str
    intent: CommandIntent
    parameters: dict[str, Any] = field(default_factory=dict)
    language: str = "de"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


@dataclass
class ChatResponse:
    command: ChatCommand
    success: bool
    message: str
    generated_files: list[GeneratedFile] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def file_paths(self) -> list[str]:
        return [f.path for f in self.generated_files]


@dataclass
class _PatternEntry:
    pattern: re.Pattern[str]
    intent: CommandIntent
    param_names: list[str]
    language: str


class CommandParser:
    """Parses natural language commands into structured ChatCommand objects."""

    def __init__(self) -> None:
        self._patterns: list[_PatternEntry] = []
        self._register_default_patterns()

    def _register_default_patterns(self) -> None:
        german = [
            (
                r"(?:baue|erstelle)\s+einen\s+neuen?\s+(\w+)[- ](\w+)[- ]bot",
                CommandIntent.CREATE_BOT,
                ["asset", "strategy"],
            ),
            (
                r"(?:baue|erstelle)\s+einen\s+(\w+)[- ]bot",
                CommandIntent.CREATE_BOT,
                ["strategy"],
            ),
            (
                r"optimiere\s+(?:die\s+)?(?:aktuelle\s+)?strategie",
                CommandIntent.OPTIMIZE_STRATEGY,
                [],
            ),
            (
                r"(?:baue|erstelle)\s+einen\s+news[- ]filter",
                CommandIntent.CREATE_NEWS_FILTER,
                [],
            ),
            (
                r"(?:baue|erstelle)\s+einen\s+(?:neuen?\s+)?indikator(?:\s+(\w+))?",
                CommandIntent.CREATE_INDICATOR,
                ["indicator_name"],
            ),
            (
                r"verbessere\s+(?:die\s+)?winrate",
                CommandIntent.OPTIMIZE_WINRATE,
                [],
            ),
            (
                r"(?:baue|erstelle)\s+einen\s+telegram[- ]signal[- ]bot",
                CommandIntent.CREATE_TELEGRAM_BOT,
                [],
            ),
            (
                r"f[üu]ge\s+trailing\s+stop\s+hinzu",
                CommandIntent.ADD_TRAILING_STOP,
                [],
            ),
            (
                r"optimiere\s+(?:den\s+)?drawdown",
                CommandIntent.OPTIMIZE_DRAWDOWN,
                [],
            ),
        ]
        english = [
            (
                r"create\s+(?:a\s+)?new\s+(\w+)[- ](\w+)\s+bot",
                CommandIntent.CREATE_BOT,
                ["asset", "strategy"],
            ),
            (
                r"create\s+(?:a\s+)?(\w+)\s+bot",
                CommandIntent.CREATE_BOT,
                ["strategy"],
            ),
            (
                r"optimize\s+(?:the\s+)?(?:current\s+)?strategy",
                CommandIntent.OPTIMIZE_STRATEGY,
                [],
            ),
            (
                r"(?:create|build)\s+(?:a\s+)?news\s+filter",
                CommandIntent.CREATE_NEWS_FILTER,
                [],
            ),
            (
                r"(?:create|build)\s+(?:a\s+)?(?:new\s+)?indicator(?:\s+(\w+))?",
                CommandIntent.CREATE_INDICATOR,
                ["indicator_name"],
            ),
            (
                r"improve\s+(?:the\s+)?win\s*rate",
                CommandIntent.OPTIMIZE_WINRATE,
                [],
            ),
            (
                r"(?:create|build)\s+(?:a\s+)?telegram\s+signal\s+bot",
                CommandIntent.CREATE_TELEGRAM_BOT,
                [],
            ),
            (
                r"add\s+trailing\s+stop",
                CommandIntent.ADD_TRAILING_STOP,
                [],
            ),
            (
                r"optimize\s+(?:the\s+)?drawdown",
                CommandIntent.OPTIMIZE_DRAWDOWN,
                [],
            ),
        ]

        for raw, intent, params in german:
            self._patterns.append(
                _PatternEntry(
                    pattern=re.compile(raw, re.IGNORECASE),
                    intent=intent,
                    param_names=params,
                    language="de",
                )
            )
        for raw, intent, params in english:
            self._patterns.append(
                _PatternEntry(
                    pattern=re.compile(raw, re.IGNORECASE),
                    intent=intent,
                    param_names=params,
                    language="en",
                )
            )

    def parse(self, text: str) -> ChatCommand:
        cleaned = text.strip()
        for entry in self._patterns:
            match = entry.pattern.search(cleaned)
            if match:
                params: dict[str, Any] = {}
                for idx, name in enumerate(entry.param_names):
                    group_idx = idx + 1
                    value = match.group(group_idx) if group_idx <= len(match.groups()) else None
                    if value:
                        params[name] = value
                return ChatCommand(
                    raw_text=cleaned,
                    intent=entry.intent,
                    parameters=params,
                    language=entry.language,
                )

        return ChatCommand(
            raw_text=cleaned,
            intent=CommandIntent.UNKNOWN,
            parameters={},
            language=self._detect_language(cleaned),
        )

    @staticmethod
    def _detect_language(text: str) -> str:
        german_markers = {"der", "die", "das", "einen", "eine", "und", "oder", "mit", "für"}
        words = set(text.lower().split())
        return "de" if words & german_markers else "en"


class ChatEngine:
    """
    Main entry-point for the conversational interface.

    Accepts a natural language string, parses it into a ChatCommand, dispatches
    code generation or system actions, and returns a ChatResponse.
    """

    def __init__(
        self,
        output_root: str | Path = "generated",
        parser: Optional[CommandParser] = None,
        generator: Optional[CodeGenerator] = None,
    ) -> None:
        self.output_root = Path(output_root)
        self.parser = parser or CommandParser()
        self.generator = generator or CodeGenerator(output_root=self.output_root)
        self._history: list[ChatResponse] = []

    @property
    def history(self) -> list[ChatResponse]:
        return list(self._history)

    def process(self, user_input: str) -> ChatResponse:
        command = self.parser.parse(user_input)
        logger.info("Parsed command: intent=%s params=%s", command.intent.name, command.parameters)

        handler = self._DISPATCH.get(command.intent, self._handle_unknown)
        response = handler(self, command)
        self._history.append(response)
        return response

    def _handle_create_bot(self, cmd: ChatCommand) -> ChatResponse:
        asset = cmd.parameters.get("asset", "EURUSD")
        strategy = cmd.parameters.get("strategy", "trend_following")
        files = self.generator.generate_bot(asset=asset, strategy=strategy)
        label = f"{asset} {strategy}" if asset != "EURUSD" or "asset" in cmd.parameters else strategy
        return ChatResponse(
            command=cmd,
            success=True,
            message=f"Bot '{label}' created successfully with {len(files)} files.",
            generated_files=files,
            suggestions=[
                "Run backtest on the new bot",
                "Optimize strategy parameters",
                "Connect to MT5 live account",
            ],
        )

    def _handle_optimize_strategy(self, cmd: ChatCommand) -> ChatResponse:
        files = self.generator.generate_optimizer_config()
        return ChatResponse(
            command=cmd,
            success=True,
            message="Strategy optimizer configuration generated.",
            generated_files=files,
            suggestions=[
                "Start optimization run",
                "Review parameter ranges",
            ],
        )

    def _handle_create_news_filter(self, cmd: ChatCommand) -> ChatResponse:
        files = self.generator.generate_news_filter()
        return ChatResponse(
            command=cmd,
            success=True,
            message="News filter module created.",
            generated_files=files,
            suggestions=["Configure news sources", "Set filter keywords"],
        )

    def _handle_create_indicator(self, cmd: ChatCommand) -> ChatResponse:
        name = cmd.parameters.get("indicator_name", "custom_indicator")
        files = self.generator.generate_indicator(name=name)
        return ChatResponse(
            command=cmd,
            success=True,
            message=f"Indicator '{name}' created.",
            generated_files=files,
            suggestions=["Backtest with the new indicator", "Add to existing strategy"],
        )

    def _handle_optimize_winrate(self, cmd: ChatCommand) -> ChatResponse:
        files = self.generator.generate_winrate_optimizer()
        return ChatResponse(
            command=cmd,
            success=True,
            message="Winrate optimization module generated.",
            generated_files=files,
            suggestions=["Run optimization", "Review filter parameters"],
        )

    def _handle_create_telegram_bot(self, cmd: ChatCommand) -> ChatResponse:
        files = self.generator.generate_telegram_signal_bot()
        return ChatResponse(
            command=cmd,
            success=True,
            message="Telegram signal bot created.",
            generated_files=files,
            suggestions=["Set Telegram API token", "Configure signal channels"],
        )

    def _handle_add_trailing_stop(self, cmd: ChatCommand) -> ChatResponse:
        files = self.generator.generate_trailing_stop_module()
        return ChatResponse(
            command=cmd,
            success=True,
            message="Trailing stop module added.",
            generated_files=files,
            suggestions=["Configure trailing distance", "Integrate with existing bot"],
        )

    def _handle_optimize_drawdown(self, cmd: ChatCommand) -> ChatResponse:
        files = self.generator.generate_drawdown_optimizer()
        return ChatResponse(
            command=cmd,
            success=True,
            message="Drawdown optimization module generated.",
            generated_files=files,
            suggestions=["Set max drawdown threshold", "Run backtest analysis"],
        )

    def _handle_unknown(self, cmd: ChatCommand) -> ChatResponse:
        return ChatResponse(
            command=cmd,
            success=False,
            message="Command not recognized. Please try one of the supported commands.",
            error="Unknown command intent",
            suggestions=[
                "Erstelle einen EURUSD-Scalping-Bot",
                "Optimiere die aktuelle Strategie",
                "Baue einen News-Filter",
                "Create a new GBPUSD-trend_following bot",
            ],
        )

    _DISPATCH: dict[CommandIntent, Any] = {
        CommandIntent.CREATE_BOT: _handle_create_bot,
        CommandIntent.OPTIMIZE_STRATEGY: _handle_optimize_strategy,
        CommandIntent.CREATE_NEWS_FILTER: _handle_create_news_filter,
        CommandIntent.CREATE_INDICATOR: _handle_create_indicator,
        CommandIntent.OPTIMIZE_WINRATE: _handle_optimize_winrate,
        CommandIntent.CREATE_TELEGRAM_BOT: _handle_create_telegram_bot,
        CommandIntent.ADD_TRAILING_STOP: _handle_add_trailing_stop,
        CommandIntent.OPTIMIZE_DRAWDOWN: _handle_optimize_drawdown,
    }
