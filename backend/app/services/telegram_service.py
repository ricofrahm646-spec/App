import httpx


class TelegramService:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    async def send_message(self, text: str) -> dict[str, str]:
        if not self.token or not self.chat_id:
            return {"status": "skipped", "detail": "Telegram credentials missing"}

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        return {"status": "sent", "detail": text}
