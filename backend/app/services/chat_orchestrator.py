"""Orchestrate chat: intent routing, code generation hooks, optional LLM."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.services.file_generator import FileGenerator
from app.services.mql5_generator import MQL5Generator, build_expert_from_prompt

logger = logging.getLogger(__name__)


@dataclass
class ChatAction:
    kind: str
    payload: dict[str, Any]


class ChatOrchestrator:
    def __init__(self) -> None:
        self.files = FileGenerator()
        self.mql5 = MQL5Generator()

    async def handle_message(self, user_text: str) -> dict[str, Any]:
        actions: list[ChatAction] = []
        lowered = user_text.lower()

        if any(k in lowered for k in ("scalp", "gold", "ea", "expert", "bot", "ict")):
            spec = build_expert_from_prompt(user_text)
            mq5 = self.mql5.expert_advisor(spec)
            rel = f"mql5/generated/{spec.name}.mq5"
            path = self.files.write_text(rel, mq5)
            actions.append(ChatAction(kind="write_mq5", payload={"path": str(path), "symbol": spec.symbol}))

        if "indikator" in lowered or "indicator" in lowered:
            name = re.sub(r"\s+", "_", user_text.strip())[:40]
            body = self.mql5.custom_indicator(name or "JarvisInd")
            rel = f"mql5/generated/{name}.mq5"
            path = self.files.write_text(rel, body)
            actions.append(ChatAction(kind="write_mq5_indicator", payload={"path": str(path)}))

        if any(k in lowered for k in ("python", "modul", "module", "news-filter", "news filter")):
            mod = self._python_stub_module(user_text)
            rel = "strategies/generated_chat_module.py"
            path = self.files.write_text(rel, mod)
            actions.append(ChatAction(kind="write_python", payload={"path": str(path)}))

        if settings.openai_api_key:
            reply = await self._llm_reply(user_text, actions)
        else:
            reply = self._fallback_reply(user_text, actions)

        return {
            "reply": reply,
            "actions": [{"kind": a.kind, "payload": a.payload} for a in actions],
        }

    def _fallback_reply(self, user_text: str, actions: list[ChatAction]) -> str:
        if not actions:
            return (
                "Ich habe noch keine automatische Aktion erkannt. "
                "Beschreibe bitte konkret, ob ein EA, Indikator oder Python-Modul entstehen soll."
            )
        parts = [a.kind for a in actions]
        return f"Aktionen ausgeführt: {', '.join(parts)}. Dateien wurden unter dem Workspace gespeichert."

    async def _llm_reply(self, user_text: str, actions: list[ChatAction]) -> str:
        system = (
            "Du bist JARVIS, ein vorsichtiger Trading-System-Assistent. "
            "Keine Garantien für Gewinne. Erkläre kurz, was gebaut wurde."
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"user": user_text, "actions": [{"kind": a.kind, "payload": a.payload} for a in actions]},
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    def _python_stub_module(self, prompt: str) -> str:
        safe = re.sub(r"[^0-9a-zA-Z_]+", "_", prompt)[:60].strip("_") or "chat_module"
        return f'''"""Auto-generated stub from JARVIS chat — implement real logic."""


def describe() -> str:
    return {prompt!r}


def on_bar(**kwargs):
    return None
'''
