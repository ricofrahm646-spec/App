"""Natural language command parser for desktop actions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ParsedIntent:
    """Represents parsed action plan from natural language."""

    original_text: str
    actions: list[dict[str, Any]]
    confidence: float


class IntentParser:
    """Parses simple natural language into structured desktop actions."""

    def parse(self, text: str) -> ParsedIntent:
        normalized = text.strip().lower()
        chunks = re.split(r"\s+and\s+|,|\s+und\s+", normalized)
        actions: list[dict[str, Any]] = []

        for chunk in chunks:
            part = chunk.strip()
            if not part:
                continue
            if part in {"jarvis, abbruch", "jarvis abbruch", "abbruch", "abort", "stop"}:
                actions.append({"type": "kill_switch"})
                continue
            if part.startswith("close ") or part.startswith("schlie"):
                app_name = part.replace("close ", "", 1).replace("schlie", "").strip(" :")
                actions.append({"type": "close_app", "app": app_name})
                continue
            if "vordergrund" in part or "focus " in part or "in den fokus" in part:
                app_name = part.replace("focus ", "").replace("in den vordergrund", "").strip()
                actions.append({"type": "focus_app", "app": app_name})
                continue
            if part.startswith("open "):
                app_name = part.replace("open ", "", 1).strip()
                if "search " in app_name:
                    first, _, query = app_name.partition("search ")
                    actions.append({"type": "open_app", "app": first.strip()})
                    actions.append({"type": "type_text", "text": query.strip()})
                    actions.append({"type": "press_key", "key": "enter"})
                else:
                    actions.append({"type": "open_app", "app": app_name})
                continue
            if part.startswith("type "):
                actions.append({"type": "type_text", "text": part.replace("type ", "", 1)})
                continue
            if part.startswith("press "):
                actions.append({"type": "press_key", "key": part.replace("press ", "", 1).strip()})
                continue
            actions.append({"type": "chat_response", "text": part})

        confidence = 0.9 if actions else 0.1
        return ParsedIntent(
            original_text=text,
            actions=actions,
            confidence=confidence,
        )

