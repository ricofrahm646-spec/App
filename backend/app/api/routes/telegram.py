"""
Telegram Router - configure bot, send messages, check status, view history.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_telegram
from app.database import get_db
from app.models.telegram_model import TelegramConfig, TelegramMessage
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


# ─────────────────────────────────────── Request models ─────────────────────

class TelegramConfigRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Telegram Bot API token")
    chat_id: str = Field(..., min_length=1, description="Target chat or group ID")


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    parse_mode: str = Field("HTML", description="HTML or Markdown")


# ─────────────────────────────────────────────────────── Helpers ─────────────

def _persist_config(db: Session, token: str, chat_id: str) -> TelegramConfig:
    """Save or update Telegram config in the database."""
    existing = db.query(TelegramConfig).first()
    if existing:
        existing.bot_token = token
        existing.chat_id = chat_id
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    config = TelegramConfig(bot_token=token, chat_id=chat_id, is_active=True)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _log_message(db: Session, text: str, success: bool, error: str = None) -> None:
    """Persist outgoing message to history."""
    try:
        msg = TelegramMessage(
            message=text,
            direction="OUT",
            status="sent" if success else "failed",
            error=error,
        )
        db.add(msg)
        db.commit()
    except Exception as exc:
        logger.warning("Could not persist telegram message: %s", exc)


def _get_db_config(db: Session) -> Optional[TelegramConfig]:
    return db.query(TelegramConfig).filter(TelegramConfig.is_active == True).first()  # noqa: E712


# ─────────────────────────────────────────────────────── Endpoints ───────────

@router.post("/configure", summary="Set Telegram bot token and chat ID", status_code=status.HTTP_201_CREATED)
async def configure_telegram(
    req: TelegramConfigRequest,
    db: Session = Depends(get_db),
    telegram: TelegramService = Depends(get_telegram),
) -> Dict[str, Any]:
    """
    Save the Telegram bot token and target chat ID.
    Initializes the bot and sends a test connection message.
    """
    success = await telegram.initialize(req.token, req.chat_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to initialize Telegram bot. Check token and chat_id.",
        )
    _persist_config(db, req.token, req.chat_id)
    return {
        "configured": True,
        "chat_id": req.chat_id,
        "message": "Telegram configured and connected successfully",
    }


@router.get("/status", summary="Telegram connection status")
def get_status(
    db: Session = Depends(get_db),
    telegram: TelegramService = Depends(get_telegram),
) -> Dict[str, Any]:
    """Check if Telegram is configured and the bot is initialized."""
    config = _get_db_config(db)
    return {
        "configured": config is not None,
        "connected": telegram._initialized,
        "chat_id": config.chat_id if config else None,
        "message_count": db.query(TelegramMessage).count(),
    }


@router.post("/test", summary="Send a test message")
async def send_test(
    db: Session = Depends(get_db),
    telegram: TelegramService = Depends(get_telegram),
) -> Dict[str, Any]:
    """Send a formatted test message to verify the Telegram setup."""
    if not telegram._initialized:
        config = _get_db_config(db)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                detail="Telegram not configured. Call POST /api/telegram/configure first.",
            )
        await telegram.initialize(config.bot_token, config.chat_id)

    test_text = (
        f"✅ <b>JARVIS AI Trading OS</b>\n\n"
        f"Telegram connection test successful!\n"
        f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    success = await telegram.send_message(test_text)
    _log_message(db, test_text, success)
    if not success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to send test message")
    return {"sent": True, "message": "Test message sent"}


@router.post("/send", summary="Send a custom message")
async def send_message(
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    telegram: TelegramService = Depends(get_telegram),
) -> Dict[str, Any]:
    """Send an arbitrary message to the configured Telegram chat."""
    if not telegram._initialized:
        config = _get_db_config(db)
        if not config:
            raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail="Telegram not configured.")
        await telegram.initialize(config.bot_token, config.chat_id)

    success = await telegram.send_message(req.message, req.parse_mode)
    _log_message(db, req.message, success)
    if not success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to send message")
    return {"sent": True}


@router.get("/history", summary="Message history")
def get_history(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return the most recent Telegram messages (newest first)."""
    messages = db.query(TelegramMessage).order_by(TelegramMessage.created_at.desc()).limit(limit).all()
    return [
        {
            "id": m.id,
            "message": m.message,
            "direction": m.direction,
            "status": m.status,
            "error": m.error,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.delete("/configure", summary="Remove Telegram configuration")
def delete_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Delete the stored Telegram bot configuration."""
    configs = db.query(TelegramConfig).all()
    if not configs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Telegram configuration found")
    for c in configs:
        db.delete(c)
    db.commit()
    return {"deleted": True, "message": "Telegram configuration removed"}
