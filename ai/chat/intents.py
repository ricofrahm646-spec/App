"""Rule-based intent parser.

Maps free-form chat messages (in English or German) to a structured intent so
the chat engine can dispatch to the right code generator. The parser is
deliberately deterministic and explainable — the LLM is used for narrative
responses, not for routing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── canonical intents ────────────────────────────────────────────
INTENT_BUILD_BOT = "build_bot"
INTENT_BUILD_INDICATOR = "build_indicator"
INTENT_OPTIMIZE = "optimize_strategy"
INTENT_IMPROVE_WINRATE = "improve_winrate"
INTENT_REDUCE_DRAWDOWN = "reduce_drawdown"
INTENT_ADD_TRAILING = "add_trailing_stop"
INTENT_ADD_NEWS_FILTER = "add_news_filter"
INTENT_TELEGRAM_BOT = "build_telegram_signal_bot"
INTENT_BACKTEST = "run_backtest"
INTENT_QUERY = "answer_question"


@dataclass
class Intent:
    name: str
    confidence: float = 1.0
    args: dict[str, Any] = field(default_factory=dict)


_SYMBOL_RE = re.compile(r"\b(?:XAU(?:USD)?|GOLD|EUR(?:USD)?|GBP(?:USD)?|USD?JPY|BTC(?:USD)?|ETH(?:USD)?|US30|NAS100|SPX500|[A-Z]{6})\b", re.I)
_TIMEFRAME_RE = re.compile(r"\b(M1|M5|M15|M30|H1|H4|D1|W1)\b", re.I)

_KIND_KEYWORDS = {
    "ict": "ict",
    "smart money": "smart_money",
    "orderblock": "smart_money",
    "liquidity": "smart_money",
    "scalp": "scalping",
    "scalping": "scalping",
    "trend": "trend_following",
    "trend-follow": "trend_following",
    "mean reversion": "mean_reversion",
    "breakout": "breakout",
    "momentum": "momentum",
    "session": "session_trading",
    "london": "session_trading",
}


def parse(message: str) -> Intent:
    m = message.lower().replace("-", " ").replace("_", " ")

    if "telegram" in m and ("signal" in m or "bot" in m):
        return Intent(INTENT_TELEGRAM_BOT)

    if any(kw in m for kw in ["trailing stop", "trailing-stop", "trail stop"]):
        return Intent(INTENT_ADD_TRAILING)

    if any(kw in m for kw in ["news filter", "news-filter", "news filtering"]):
        return Intent(INTENT_ADD_NEWS_FILTER)

    if any(kw in m for kw in ["optimise", "optimize", "optimier", "improve drawdown",
                              "reduce drawdown", "lower drawdown"]):
        if "drawdown" in m:
            return Intent(INTENT_REDUCE_DRAWDOWN, args=_strategy_args(message))
        return Intent(INTENT_OPTIMIZE, args=_strategy_args(message))

    if any(kw in m for kw in ["improve winrate", "verbessere die winrate", "increase winrate"]):
        return Intent(INTENT_IMPROVE_WINRATE, args=_strategy_args(message))

    if any(kw in m for kw in ["backtest", "back-test", "back test"]):
        return Intent(INTENT_BACKTEST, args=_strategy_args(message))

    if any(kw in m for kw in ["indikator", "indicator"]):
        return Intent(INTENT_BUILD_INDICATOR, args={"name": _extract_name(message)})

    if any(kw in m for kw in ["build", "baue", "erstelle", "create", "neuer bot", "new bot"]):
        return Intent(INTENT_BUILD_BOT, args=_strategy_args(message))

    return Intent(INTENT_QUERY, confidence=0.3)


# ── helpers ──────────────────────────────────────────────────────
def _strategy_args(message: str) -> dict[str, Any]:
    m = message.lower()
    args: dict[str, Any] = {}

    for kw, kind in _KIND_KEYWORDS.items():
        if kw in m:
            args["kind"] = kind
            break

    sym_match = _SYMBOL_RE.search(message)
    if sym_match:
        sym = sym_match.group(0).upper().replace("GOLD", "XAUUSD")
        args["symbol"] = sym if len(sym) >= 6 else sym + "USD"

    tf_match = _TIMEFRAME_RE.search(message)
    if tf_match:
        args["timeframe"] = tf_match.group(0).upper()

    args["name"] = _extract_name(message)
    return args


def _extract_name(message: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9 ]+", " ", message).strip().split()
    if not base:
        return "JarvisBot"
    candidate = "".join(w.title() for w in base[:5])
    return candidate or "JarvisBot"
