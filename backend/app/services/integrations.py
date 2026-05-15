import httpx


class TelegramService:
    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send_message(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={"chat_id": self.chat_id, "text": text})
            response.raise_for_status()
        return True


class TradingViewService:
    def __init__(self, shared_secret: str | None) -> None:
        self.shared_secret = shared_secret

    def validate_symbol(self, symbol: str) -> bool:
        allowed = {
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "USDCHF",
            "AUDUSD",
            "USDCAD",
            "NZDUSD",
        }
        return symbol.upper() in allowed

    def build_webhook_payload(self, *, symbol: str, action: str, stop_loss: float, take_profit: float) -> dict[str, str | float]:
        if not self.validate_symbol(symbol):
            raise ValueError("TradingView integration is restricted to supported Forex pairs.")

        return {
            "secret": self.shared_secret or "configure-me",
            "symbol": symbol.upper(),
            "action": action.lower(),
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
