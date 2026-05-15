"""Chat engine end-to-end (using the local LLM fallback)."""
from __future__ import annotations

import asyncio

from ai.chat.engine import ChatEngine


def test_build_bot_generates_artefacts():
    engine = ChatEngine()
    turn = asyncio.run(engine.handle("Build a gold scalping bot for XAUUSD M5"))
    assert turn.role == "assistant"
    artefacts = turn.meta["artefacts"]
    assert "ea_path" in artefacts
    assert "python_path" in artefacts
    assert artefacts["kind"] == "scalping"
    assert artefacts["symbol"] == "XAUUSD"


def test_trailing_stop_intent():
    engine = ChatEngine()
    turn = asyncio.run(engine.handle("Add a trailing stop"))
    assert turn.intent == "add_trailing_stop"
