import httpx


class TelegramService:
    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_message(self, text: str) -> dict[str, str | bool]:
        if not self.configured():
            return {"sent": False, "reason": "Telegram bot token or chat id is not configured"}

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json={"chat_id": self.chat_id, "text": text})
            response.raise_for_status()
        return {"sent": True, "reason": "Message delivered"}

    @staticmethod
    def trade_message(event: str, symbol: str, pnl: float | None = None) -> str:
        suffix = "" if pnl is None else f" | P/L: {pnl:.2f}"
        return f"JARVIS {event.upper()} | {symbol}{suffix}"
