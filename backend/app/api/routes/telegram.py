from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.dependencies import telegram_service

router = APIRouter()


class TelegramMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@router.post("/send")
async def send_telegram_message(payload: TelegramMessageRequest) -> dict[str, str]:
    return await telegram_service.send_message(payload.text)
