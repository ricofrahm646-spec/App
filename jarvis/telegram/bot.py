import httpx

class TelegramBot:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    async def send_message(self, text: str):
        if not self.token or not self.chat_id:
            print(f"Telegram not configured. Log: {text}")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": f"🤖 JARVIS AI ALERT 🤖\n\n{text}",
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.api_url, json=payload)
                return response.status_code == 200
            except Exception as e:
                print(f"Telegram error: {e}")
                return False

    async def broadcast_signal(self, symbol, direction, price, sl, tp):
        msg = (f"*SIGNAL: {symbol}*\n"
               f"Direction: {direction}\n"
               f"Price: {price}\n"
               f"SL: {sl}\n"
               f"TP: {tp}")
        return await self.send_message(msg)
