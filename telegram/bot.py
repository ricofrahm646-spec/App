"""Telegram bot wrapper.

Sends trade notifications (buy / sell / open / close / pnl / risk warnings) to
the configured chat. Credentials are loaded from settings and can be updated
at runtime via the `/api/telegram/configure` endpoint.
"""
from __future__ import annotations

from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger


class TelegramService:
    _instance: "TelegramService | None" = None

    def __init__(self, token: str = "", chat_id: str = "") -> None:
        self._token = token or settings.telegram_bot_token
        self._chat_id = chat_id or settings.telegram_chat_id

    @classmethod
    def instance(cls) -> "TelegramService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def update_credentials(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id

    async def send(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.is_configured:
            logger.debug("Telegram not configured — skipping: {}", text[:60])
            return False
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.post(
                    url, json={"chat_id": self._chat_id, "text": text, "parse_mode": parse_mode}
                )
                r.raise_for_status()
                return True
            except httpx.HTTPError as exc:
                logger.warning("Telegram send failed: {}", exc)
                return False

    async def notify_trade(self, action: str, payload: dict[str, Any]) -> None:
        symbol = payload.get("symbol", "?")
        side = payload.get("side", "?")
        volume = payload.get("volume", "?")
        pnl = payload.get("profit", 0.0)
        text = (
            f"*JARVIS* — {action}\n"
            f"`{symbol}` {side} {volume}\n"
            f"P/L: `{pnl:+.2f}`"
        )
        await self.send(text)
