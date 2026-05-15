import logging

import httpx


logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    async def send_message(self, message: str) -> bool:
        if not self.token or not self.chat_id:
            logger.info("Telegram not configured, skipping notification.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        return True
