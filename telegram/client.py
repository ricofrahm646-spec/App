from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class TelegramConfig:
    token: str | None
    chat_id: str | None


class TelegramNotifier:
    """Async Telegram Bot API client for JARVIS alerts."""

    def __init__(self, config: TelegramConfig) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.token and self.config.chat_id)

    async def send_message(self, text: str) -> dict[str, Any]:
        if not self.is_configured:
            return {"sent": False, "reason": "Telegram token or chat_id missing."}

        url = f"https://api.telegram.org/bot{self.config.token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json={"chat_id": self.config.chat_id, "text": text, "parse_mode": "HTML"},
            )
        return {"sent": response.is_success, "status_code": response.status_code}

    async def send_trade_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        text = (
            "<b>JARVIS Signal</b>\n"
            f"Symbol: {signal.get('symbol')}\n"
            f"Side: {signal.get('side')}\n"
            f"Strategy: {signal.get('strategy', 'unknown')}\n"
            f"Risk: {signal.get('risk_percent', 'n/a')}%"
        )
        return await self.send_message(text)

    async def send_risk_warning(self, message: str) -> dict[str, Any]:
        return await self.send_message(f"<b>JARVIS Risk Warning</b>\n{message}")
