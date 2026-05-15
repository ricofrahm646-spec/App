"""High-level chat orchestrator.

Pipeline:
1. The intent parser classifies the user message.
2. The dispatcher executes the corresponding generator (strategy / EA / Pine / Telegram).
3. The LLM router crafts a natural-language response describing what was done.

All side effects (file generation, DB updates) happen inside this module so
the API layer stays thin.
"""
from __future__ import annotations

from typing import Any

from ai.chat import intents as intent_module
from ai.chat.llm import LLMRouter
from ai.codegen.python_generator import PythonStrategyGenerator
from backend.app.core.logging_setup import logger
from backend.app.schemas.common import ChatTurn
from mql5.generator import MQL5Generator
from tradingview.pine_generator import PineGenerator


class ChatEngine:
    def __init__(self) -> None:
        self.llm = LLMRouter()
        self.mql5 = MQL5Generator()
        self.pine = PineGenerator()
        self.py = PythonStrategyGenerator()

    async def handle(self, message: str) -> ChatTurn:
        intent = intent_module.parse(message)
        logger.info("Chat intent: {} args={}", intent.name, intent.args)

        artefacts: dict[str, Any] = {}

        if intent.name == intent_module.INTENT_BUILD_BOT:
            artefacts = self._build_bot(intent.args)
        elif intent.name == intent_module.INTENT_BUILD_INDICATOR:
            artefacts = self._build_indicator(intent.args)
        elif intent.name in {
            intent_module.INTENT_OPTIMIZE,
            intent_module.INTENT_REDUCE_DRAWDOWN,
            intent_module.INTENT_IMPROVE_WINRATE,
        }:
            artefacts = {"optimization": intent.name, "args": intent.args}
        elif intent.name == intent_module.INTENT_ADD_TRAILING:
            artefacts = {"feature": "trailing_stop", "note": "Trailing stop module enabled in EA template."}
        elif intent.name == intent_module.INTENT_ADD_NEWS_FILTER:
            artefacts = {"feature": "news_filter", "note": "News filter scaffold added to risk engine."}
        elif intent.name == intent_module.INTENT_TELEGRAM_BOT:
            artefacts = {"telegram": "Telegram signal bot is included; configure token in /api/telegram/configure."}
        elif intent.name == intent_module.INTENT_BACKTEST:
            artefacts = {"backtest": "Send POST /api/backtest/run with the desired strategy."}

        prompt = self._format_prompt(message, intent.name, artefacts)
        llm_resp = await self.llm.complete(prompt)
        content = llm_resp.content.strip() or self._default_message(intent.name, artefacts)

        return ChatTurn(
            role="assistant",
            content=content,
            intent=intent.name,
            meta={"args": intent.args, "artefacts": artefacts, "provider": llm_resp.provider},
        )

    # ── builders ─────────────────────────────────────────────────
    def _build_bot(self, args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name", "JarvisBot")
        kind = args.get("kind", "trend_following")
        symbol = args.get("symbol", "EURUSD")
        timeframe = args.get("timeframe", "M15")
        parameters = args.get("parameters", {})

        mq5_path = self.mql5.generate_ea(
            name=name, symbol=symbol, timeframe=timeframe, strategy_kind=kind, parameters=parameters
        )
        py_path = self.py.generate_strategy(name=name, kind=kind, parameters=parameters)
        pine_code = self.pine.generate(name=name, kind=kind, parameters=parameters)

        return {
            "ea_path": str(mq5_path),
            "python_path": str(py_path),
            "pine_preview": pine_code.splitlines()[:5],
            "symbol": symbol,
            "timeframe": timeframe,
            "kind": kind,
        }

    def _build_indicator(self, args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name", "JarvisIndicator")
        kind = args.get("kind", "rsi_divergence")
        path = self.mql5.generate_indicator(name=name, kind=kind, parameters={})
        return {"indicator_path": str(path), "kind": kind}

    # ── llm prompt ──────────────────────────────────────────────
    def _format_prompt(self, user_message: str, intent: str, artefacts: dict[str, Any]) -> str:
        return (
            f"User said: {user_message!r}\n"
            f"Detected intent: {intent}\n"
            f"Generated artefacts: {artefacts}\n"
            "Reply in 2-4 short sentences. Summarise what JARVIS did and propose the next step. "
            "Reference the file paths created. Do not promise profits."
        )

    @staticmethod
    def _default_message(intent: str, artefacts: dict[str, Any]) -> str:
        if artefacts:
            return f"Done. Intent={intent}. Output: {artefacts}"
        return "I'm here to help. Try: 'Build an ICT bot for EURUSD M5'."
