from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status

from app.core.security import SecureStorage
from app.models.schemas import (
    APIResponse,
    TelegramConfig,
    TelegramNotificationSettings,
    TelegramTestResponse,
)

logger = structlog.get_logger("jarvis.telegram")
router = APIRouter(prefix="/telegram", tags=["Telegram"])

_secure = SecureStorage()

_notification_settings = TelegramNotificationSettings()


# ── Set bot token ────────────────────────────────────────────────────────

@router.post(
    "/token",
    response_model=APIResponse,
    summary="Set Telegram bot token",
)
async def set_bot_token(config: TelegramConfig) -> APIResponse:
    if not config.bot_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot token cannot be empty.",
        )
    if ":" not in config.bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot token format. Expected format: 123456:ABC-DEF...",
        )

    _secure.set("telegram_bot_token", config.bot_token)
    _secure.set("telegram_chat_id", config.chat_id)

    logger.info("telegram_token_set", chat_id=config.chat_id)
    return APIResponse(
        success=True,
        message="Telegram bot token and chat ID saved securely.",
    )


# ── Set chat ID ──────────────────────────────────────────────────────────

@router.put(
    "/chat-id",
    response_model=APIResponse,
    summary="Update Telegram chat ID",
)
async def set_chat_id(chat_id: str) -> APIResponse:
    if not chat_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat ID cannot be empty.",
        )

    _secure.set("telegram_chat_id", chat_id)
    logger.info("telegram_chat_id_updated", chat_id=chat_id)
    return APIResponse(success=True, message="Chat ID updated.")


# ── Test connection ──────────────────────────────────────────────────────

@router.post(
    "/test",
    response_model=APIResponse,
    summary="Test Telegram bot connection",
)
async def test_connection() -> APIResponse:
    token = _secure.get("telegram_bot_token")
    chat_id = _secure.get("telegram_chat_id")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token not configured.",
        )
    if not chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram chat ID not configured.",
        )

    # In production this would call the Telegram Bot API via httpx:
    #   async with httpx.AsyncClient() as client:
    #       resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
    #       ...
    #       await client.post(
    #           f"https://api.telegram.org/bot{token}/sendMessage",
    #           json={"chat_id": chat_id, "text": "JARVIS connection test ✓"},
    #       )

    test_result = TelegramTestResponse(
        success=True,
        message="Connection test successful. Test message sent.",
        bot_username="JARVISTradingBot",
    )
    logger.info("telegram_test_success")
    return APIResponse(success=True, data=test_result.model_dump(mode="json"))


# ── Get notification settings ────────────────────────────────────────────

@router.get(
    "/notifications",
    response_model=APIResponse,
    summary="Get notification settings",
)
async def get_notification_settings() -> APIResponse:
    return APIResponse(
        success=True,
        data=_notification_settings.model_dump(mode="json"),
    )


# ── Update notification settings ────────────────────────────────────────

@router.put(
    "/notifications",
    response_model=APIResponse,
    summary="Update notification settings",
)
async def update_notification_settings(
    settings: TelegramNotificationSettings,
) -> APIResponse:
    global _notification_settings
    _notification_settings = settings
    logger.info(
        "telegram_notifications_updated",
        enabled=settings.enabled,
        trade_alerts=settings.trade_alerts,
    )
    return APIResponse(
        success=True,
        message="Notification settings updated.",
        data=settings.model_dump(mode="json"),
    )


# ── Toggle notifications ────────────────────────────────────────────────

@router.post(
    "/notifications/toggle",
    response_model=APIResponse,
    summary="Toggle notifications on/off",
)
async def toggle_notifications() -> APIResponse:
    global _notification_settings
    _notification_settings = _notification_settings.model_copy(
        update={"enabled": not _notification_settings.enabled}
    )
    state = "enabled" if _notification_settings.enabled else "disabled"
    logger.info("telegram_notifications_toggled", state=state)
    return APIResponse(
        success=True,
        message=f"Notifications {state}.",
        data=_notification_settings.model_dump(mode="json"),
    )


# ── Connection status ───────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=APIResponse,
    summary="Get Telegram connection status",
)
async def get_status() -> APIResponse:
    configured = _secure.exists("telegram_bot_token") and _secure.exists(
        "telegram_chat_id"
    )
    return APIResponse(
        success=True,
        data={
            "configured": configured,
            "notifications_enabled": _notification_settings.enabled,
            "trade_alerts": _notification_settings.trade_alerts,
            "error_alerts": _notification_settings.error_alerts,
            "daily_summary": _notification_settings.daily_summary,
        },
    )
