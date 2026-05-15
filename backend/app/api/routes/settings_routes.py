"""Application settings management routes.

Endpoints
---------
GET /           – retrieve current (non-secret) settings
PUT /telegram   – update Telegram configuration
PUT /mt5        – update MT5 configuration
PUT /risk       – update risk management parameters
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import decrypt_api_key, encrypt_api_key

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TelegramConfig(BaseModel):
    """Payload for updating Telegram settings."""

    bot_token: str = Field(..., min_length=1)
    chat_id: str = Field(..., min_length=1)


class MT5Config(BaseModel):
    """Payload for updating MT5 connection settings."""

    path: Optional[str] = None
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    data_path: Optional[str] = None


class RiskConfig(BaseModel):
    """Payload for updating risk management parameters."""

    max_risk_per_trade: Optional[float] = Field(None, ge=0.001, le=1.0)
    max_daily_loss: Optional[float] = Field(None, ge=0.001, le=1.0)
    max_drawdown: Optional[float] = Field(None, ge=0.01, le=1.0)
    max_concurrent_trades: Optional[int] = Field(None, ge=1, le=100)
    emergency_stop_loss_pct: Optional[float] = Field(None, ge=0.01, le=1.0)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _safe_settings() -> dict[str, Any]:
    """Return current settings with secrets masked."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "telegram": {
            "bot_token_set": bool(settings.TELEGRAM_BOT_TOKEN),
            "chat_id": settings.TELEGRAM_CHAT_ID or None,
        },
        "mt5": {
            "path": settings.MT5_PATH or None,
            "login": settings.MT5_LOGIN or None,
            "server": settings.MT5_SERVER or None,
            "data_path": settings.MT5_DATA_PATH or None,
        },
        "risk": {
            "max_risk_per_trade": settings.MAX_RISK_PER_TRADE,
            "max_daily_loss": settings.MAX_DAILY_LOSS,
            "max_drawdown": settings.MAX_DRAWDOWN,
            "max_concurrent_trades": settings.MAX_CONCURRENT_TRADES,
            "emergency_stop_loss_pct": settings.EMERGENCY_STOP_LOSS_PCT,
        },
        "ai": {
            "model_path": settings.AI_MODEL_PATH,
            "openai_key_set": bool(settings.OPENAI_API_KEY),
        },
        "tradingview": {
            "webhook_secret_set": bool(settings.TRADINGVIEW_WEBHOOK_SECRET),
        },
    }


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Return current application settings with secrets masked."""
    return _safe_settings()


@router.put("/telegram")
async def update_telegram(payload: TelegramConfig) -> dict[str, str]:
    """Update Telegram bot configuration.

    In production, persist these to an encrypted store or DB table rather than
    mutating the in-memory singleton.
    """
    settings.TELEGRAM_BOT_TOKEN = payload.bot_token
    settings.TELEGRAM_CHAT_ID = payload.chat_id
    return {"status": "ok", "message": "Telegram configuration updated"}


@router.put("/mt5")
async def update_mt5(payload: MT5Config) -> dict[str, str]:
    """Update MetaTrader 5 connection settings."""
    if payload.path is not None:
        settings.MT5_PATH = payload.path
    if payload.login is not None:
        settings.MT5_LOGIN = payload.login
    if payload.password is not None:
        settings.MT5_PASSWORD = payload.password
    if payload.server is not None:
        settings.MT5_SERVER = payload.server
    if payload.data_path is not None:
        settings.MT5_DATA_PATH = payload.data_path
    return {"status": "ok", "message": "MT5 configuration updated"}


@router.put("/risk")
async def update_risk(payload: RiskConfig) -> dict[str, Any]:
    """Update risk management parameters."""
    updated: dict[str, Any] = {}
    if payload.max_risk_per_trade is not None:
        settings.MAX_RISK_PER_TRADE = payload.max_risk_per_trade
        updated["max_risk_per_trade"] = payload.max_risk_per_trade
    if payload.max_daily_loss is not None:
        settings.MAX_DAILY_LOSS = payload.max_daily_loss
        updated["max_daily_loss"] = payload.max_daily_loss
    if payload.max_drawdown is not None:
        settings.MAX_DRAWDOWN = payload.max_drawdown
        updated["max_drawdown"] = payload.max_drawdown
    if payload.max_concurrent_trades is not None:
        settings.MAX_CONCURRENT_TRADES = payload.max_concurrent_trades
        updated["max_concurrent_trades"] = payload.max_concurrent_trades
    if payload.emergency_stop_loss_pct is not None:
        settings.EMERGENCY_STOP_LOSS_PCT = payload.emergency_stop_loss_pct
        updated["emergency_stop_loss_pct"] = payload.emergency_stop_loss_pct

    return {"status": "ok", "message": "Risk parameters updated", "updated": updated}
