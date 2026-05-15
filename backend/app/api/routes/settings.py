from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.core.security import SecureStorage
from app.models.schemas import (
    AISettings,
    AllSettings,
    APIResponse,
    GeneralSettings,
    MT5ConnectionSettings,
)

logger = structlog.get_logger("jarvis.settings")
router = APIRouter(prefix="/settings", tags=["Settings"])

_secure = SecureStorage()

_current_settings = AllSettings()


# ── Get all settings ─────────────────────────────────────────────────────

@router.get(
    "",
    response_model=APIResponse,
    summary="Get all application settings",
)
async def get_all_settings() -> APIResponse:
    safe = _current_settings.model_copy(deep=True)
    if safe.ai.api_key:
        safe.ai.api_key = safe.ai.api_key[:8] + "..." + safe.ai.api_key[-4:]
    if safe.mt5.password:
        safe.mt5.password = "********"
    return APIResponse(success=True, data=safe.model_dump(mode="json"))


# ── Update all settings ─────────────────────────────────────────────────

@router.put(
    "",
    response_model=APIResponse,
    summary="Update all application settings",
)
async def update_all_settings(settings: AllSettings) -> APIResponse:
    global _current_settings

    if settings.ai.api_key and settings.ai.api_key not in ("", "********"):
        _secure.set("ai_api_key", settings.ai.api_key)

    if settings.mt5.password and settings.mt5.password != "********":
        _secure.set("mt5_password", settings.mt5.password)

    _current_settings = settings
    logger.info("all_settings_updated")
    return APIResponse(
        success=True,
        message="Settings updated.",
    )


# ── General settings ────────────────────────────────────────────────────

@router.get(
    "/general",
    response_model=APIResponse,
    summary="Get general settings",
)
async def get_general_settings() -> APIResponse:
    return APIResponse(
        success=True,
        data=_current_settings.general.model_dump(mode="json"),
    )


@router.put(
    "/general",
    response_model=APIResponse,
    summary="Update general settings",
)
async def update_general_settings(settings: GeneralSettings) -> APIResponse:
    global _current_settings
    _current_settings = _current_settings.model_copy(
        update={"general": settings}
    )
    logger.info("general_settings_updated")
    return APIResponse(
        success=True,
        message="General settings updated.",
        data=settings.model_dump(mode="json"),
    )


# ── MT5 connection settings ─────────────────────────────────────────────

@router.get(
    "/mt5",
    response_model=APIResponse,
    summary="Get MT5 connection settings",
)
async def get_mt5_settings() -> APIResponse:
    safe = _current_settings.mt5.model_copy()
    if safe.password:
        safe = safe.model_copy(update={"password": "********"})
    return APIResponse(success=True, data=safe.model_dump(mode="json"))


@router.put(
    "/mt5",
    response_model=APIResponse,
    summary="Update MT5 connection settings",
)
async def update_mt5_settings(settings: MT5ConnectionSettings) -> APIResponse:
    global _current_settings

    if settings.password and settings.password != "********":
        _secure.set("mt5_password", settings.password)

    _current_settings = _current_settings.model_copy(update={"mt5": settings})
    logger.info(
        "mt5_settings_updated",
        host=settings.host,
        port=settings.port,
        account=settings.account,
    )
    return APIResponse(
        success=True,
        message="MT5 connection settings updated.",
        data=_current_settings.mt5.model_copy(
            update={"password": "********"} if settings.password else {}
        ).model_dump(mode="json"),
    )


# ── MT5 connection test ─────────────────────────────────────────────────

@router.post(
    "/mt5/test",
    response_model=APIResponse,
    summary="Test MT5 connection",
)
async def test_mt5_connection() -> APIResponse:
    mt5 = _current_settings.mt5
    if not mt5.account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MT5 account number not configured.",
        )

    # In production this would attempt an actual connection to the MT5 bridge.
    logger.info(
        "mt5_connection_test",
        host=mt5.host,
        port=mt5.port,
        account=mt5.account,
    )
    return APIResponse(
        success=True,
        message="MT5 connection test initiated.",
        data={
            "host": mt5.host,
            "port": mt5.port,
            "account": mt5.account,
            "server": mt5.server,
            "status": "simulated_ok",
        },
    )


# ── AI settings ──────────────────────────────────────────────────────────

@router.get(
    "/ai",
    response_model=APIResponse,
    summary="Get AI/LLM settings",
)
async def get_ai_settings() -> APIResponse:
    safe = _current_settings.ai.model_copy()
    if safe.api_key:
        safe = safe.model_copy(
            update={"api_key": safe.api_key[:8] + "..." + safe.api_key[-4:]}
        )
    return APIResponse(success=True, data=safe.model_dump(mode="json"))


@router.put(
    "/ai",
    response_model=APIResponse,
    summary="Update AI/LLM settings",
)
async def update_ai_settings(settings: AISettings) -> APIResponse:
    global _current_settings

    if settings.api_key and settings.api_key not in ("", "********"):
        _secure.set("ai_api_key", settings.api_key)

    _current_settings = _current_settings.model_copy(update={"ai": settings})
    logger.info("ai_settings_updated", provider=settings.provider, model=settings.model)
    return APIResponse(
        success=True,
        message="AI settings updated.",
    )


# ── Export / Import ──────────────────────────────────────────────────────

@router.get(
    "/export",
    response_model=APIResponse,
    summary="Export settings (without secrets)",
)
async def export_settings() -> APIResponse:
    export = _current_settings.model_copy(deep=True)
    export.ai.api_key = ""
    export.mt5.password = ""
    return APIResponse(
        success=True,
        message="Settings exported (secrets excluded).",
        data=export.model_dump(mode="json"),
    )


@router.post(
    "/import",
    response_model=APIResponse,
    summary="Import settings from exported config",
)
async def import_settings(settings: AllSettings) -> APIResponse:
    global _current_settings
    existing_api_key = _current_settings.ai.api_key
    existing_mt5_pass = _current_settings.mt5.password

    _current_settings = settings
    if not settings.ai.api_key:
        _current_settings = _current_settings.model_copy(
            update={"ai": settings.ai.model_copy(update={"api_key": existing_api_key})}
        )
    if not settings.mt5.password:
        _current_settings = _current_settings.model_copy(
            update={"mt5": settings.mt5.model_copy(update={"password": existing_mt5_pass})}
        )

    logger.info("settings_imported")
    return APIResponse(success=True, message="Settings imported.")
