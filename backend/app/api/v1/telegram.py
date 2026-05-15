"""Telegram test hook."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.telegram_client import TelegramService

router = APIRouter()
_service = TelegramService()


class TelegramTest(BaseModel):
    text: str = Field(default="JARVIS connectivity test", max_length=3500)


@router.post("/send-test")
async def send_test(body: TelegramTest):
    return await _service.send_message(body.text)
