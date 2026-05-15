"""TradingView webhook receiver."""

from fastapi import APIRouter, Header, Request

from app.services.telegram_client import TelegramService
from app.services.tradingview_webhooks import TradingViewAlert, verify_secret

router = APIRouter()
_telegram = TelegramService()


@router.post("/webhook")
async def webhook(
    request: Request,
    x_tv_secret: str | None = Header(default=None, alias="X-TV-SECRET"),
):
    raw = await request.json()
    alert = TradingViewAlert.model_validate(raw)
    if not verify_secret(alert, x_tv_secret):
        return {"ok": False, "error": "unauthorized"}
    await _telegram.send_message(f"TradingView alert: {raw}")
    return {"ok": True}
