"""Intent parser unit tests (multi-language)."""
from __future__ import annotations

import pytest

from ai.chat import intents


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Baue einen neuen Gold-Scalping-Bot", intents.INTENT_BUILD_BOT),
        ("Build a new gold scalping bot", intents.INTENT_BUILD_BOT),
        ("Erstelle einen ICT-Bot", intents.INTENT_BUILD_BOT),
        ("Optimiere die aktuelle Strategie", intents.INTENT_OPTIMIZE),
        ("Baue einen News-Filter", intents.INTENT_ADD_NEWS_FILTER),
        ("Erstelle einen neuen Indikator", intents.INTENT_BUILD_INDICATOR),
        ("Verbessere die Winrate", intents.INTENT_IMPROVE_WINRATE),
        ("Baue einen Telegram-Signal-Bot", intents.INTENT_TELEGRAM_BOT),
        ("Füge Trailing Stop hinzu", intents.INTENT_ADD_TRAILING),
        ("Reduce drawdown", intents.INTENT_REDUCE_DRAWDOWN),
        ("Run a backtest on EURUSD", intents.INTENT_BACKTEST),
    ],
)
def test_parse(message: str, expected: str):
    assert intents.parse(message).name == expected


def test_extract_symbol_and_kind():
    intent = intents.parse("Build a gold scalping bot for XAUUSD M5")
    assert intent.args["kind"] == "scalping"
    assert intent.args["symbol"] == "XAUUSD"
    assert intent.args["timeframe"] == "M5"
