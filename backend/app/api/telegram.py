from fastapi import APIRouter, Depends

from backend.app.dependencies import get_telegram_notifier
from backend.app.schemas import TelegramSettingsRequest
from telegram.client import TelegramNotifier

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/settings")
async def save_settings(request: TelegramSettingsRequest) -> dict:
    # Production persistence should use SecretVault + database.SecretReference.
    return {
        "saved": True,
        "message": "Settings accepted. Persist encrypted values through the database layer in production.",
        "token_preview": f"{request.token[:4]}...",
        "chat_id": request.chat_id,
    }


@router.post("/test")
async def test_message(notifier: TelegramNotifier = Depends(get_telegram_notifier)) -> dict:
    return await notifier.send_message("JARVIS Telegram integration test.")
