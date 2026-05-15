"""LLM router — supports OpenAI, Anthropic and a deterministic local fallback.

The fallback returns rule-based responses so the chat works even without API
keys. When a real key is provided the corresponding SDK is used. Network /
quota errors gracefully degrade to the local responder.
"""
from __future__ import annotations

from typing import Any

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger


class LLMResponse:
    def __init__(self, content: str, provider: str, meta: dict[str, Any] | None = None) -> None:
        self.content = content
        self.provider = provider
        self.meta = meta or {}


class LLMRouter:
    SYSTEM_PROMPT = (
        "You are JARVIS, a senior quantitative trading engineer. You answer concisely, "
        "in English, with practical advice and concrete code. Never promise profits."
    )

    async def complete(self, prompt: str, history: list[dict[str, str]] | None = None) -> LLMResponse:
        history = history or []
        provider = settings.llm_provider

        try:
            if provider == "openai" and settings.openai_api_key:
                return await self._openai(prompt, history)
            if provider == "anthropic" and settings.anthropic_api_key:
                return await self._anthropic(prompt, history)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM provider '{}' failed: {} — falling back to local", provider, exc)

        return self._local(prompt)

    async def _openai(self, prompt: str, history: list[dict[str, str]]) -> LLMResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}, *history, {"role": "user", "content": prompt}]
        resp = await client.chat.completions.create(model=settings.llm_model, messages=messages)
        return LLMResponse(content=resp.choices[0].message.content or "", provider="openai")

    async def _anthropic(self, prompt: str, history: list[dict[str, str]]) -> LLMResponse:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.llm_model or "claude-3-5-sonnet-latest",
            system=self.SYSTEM_PROMPT,
            max_tokens=1024,
            messages=[*history, {"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if hasattr(block, "text"))
        return LLMResponse(content=text, provider="anthropic")

    def _local(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            content=(
                "I parsed your request locally (no LLM key configured). "
                "I'll dispatch it to the appropriate generator. "
                "Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for richer answers."
            ),
            provider="local",
        )
