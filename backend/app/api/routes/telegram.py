"""Telegram bot control endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from telegram.bot import TelegramService

router = APIRouter()


class TelegramConfig(BaseModel):
    token: str
    chat_id: str


@router.post("/configure")
async def configure(cfg: TelegramConfig) -> dict[str, str]:
    svc = TelegramService.instance()
    svc.update_credentials(cfg.token, cfg.chat_id)
    return {"status": "configured"}


class TelegramMessage(BaseModel):
    text: str


@router.post("/send")
async def send(msg: TelegramMessage) -> dict[str, str]:
    svc = TelegramService.instance()
    await svc.send(msg.text)
    return {"status": "sent"}


@router.get("/status")
async def status() -> dict[str, bool]:
    svc = TelegramService.instance()
    return {"configured": svc.is_configured}
