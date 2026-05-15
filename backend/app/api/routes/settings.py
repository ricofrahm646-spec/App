from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, encrypt_field, decrypt_field
from app.models.user import User, UserSettings

router = APIRouter(prefix="/settings", tags=["User Settings"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class SettingsRead(BaseModel):
    """Settings representation – sensitive values are masked."""
    id: int
    user_id: int
    telegram_chat_id: Optional[str]
    telegram_token_set: bool
    mt5_login: Optional[int]
    mt5_server: Optional[str]
    mt5_password_set: bool
    mt5_path: Optional[str]
    tradingview_secret: Optional[str]
    max_trades: Optional[int]
    max_drawdown_percent: Optional[float]
    default_lot_size: Optional[float]

    model_config = {"from_attributes": False}

    @classmethod
    def from_orm(cls, s: UserSettings) -> "SettingsRead":
        return cls(
            id=s.id,
            user_id=s.user_id,
            telegram_chat_id=s.telegram_chat_id,
            telegram_token_set=bool(s.telegram_token),
            mt5_login=s.mt5_login,
            mt5_server=s.mt5_server,
            mt5_password_set=bool(s.mt5_password),
            mt5_path=s.mt5_path,
            tradingview_secret=s.tradingview_secret,
            max_trades=s.max_trades,
            max_drawdown_percent=s.max_drawdown_percent,
            default_lot_size=s.default_lot_size,
        )


class SettingsUpdate(BaseModel):
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    mt5_path: Optional[str] = None
    tradingview_secret: Optional[str] = None
    max_trades: Optional[int] = None
    max_drawdown_percent: Optional[float] = None
    default_lot_size: Optional[float] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

async def _get_or_create_settings(
    user: User, db: AsyncSession
) -> UserSettings:
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.flush()
    return settings


@router.get("/", response_model=SettingsRead)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsRead:
    s = await _get_or_create_settings(current_user, db)
    await db.commit()
    return SettingsRead.from_orm(s)


@router.put("/", response_model=SettingsRead)
async def update_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsRead:
    s = await _get_or_create_settings(current_user, db)

    if payload.telegram_token is not None:
        s.telegram_token = encrypt_field(payload.telegram_token)
    if payload.telegram_chat_id is not None:
        s.telegram_chat_id = payload.telegram_chat_id
    if payload.mt5_login is not None:
        s.mt5_login = payload.mt5_login
    if payload.mt5_password is not None:
        s.mt5_password = encrypt_field(payload.mt5_password)
    if payload.mt5_server is not None:
        s.mt5_server = payload.mt5_server
    if payload.mt5_path is not None:
        s.mt5_path = payload.mt5_path
    if payload.tradingview_secret is not None:
        s.tradingview_secret = payload.tradingview_secret
    if payload.max_trades is not None:
        s.max_trades = payload.max_trades
    if payload.max_drawdown_percent is not None:
        s.max_drawdown_percent = payload.max_drawdown_percent
    if payload.default_lot_size is not None:
        s.default_lot_size = payload.default_lot_size

    await db.commit()
    await db.refresh(s)
    return SettingsRead.from_orm(s)
