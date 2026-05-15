from __future__ import annotations

import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Header, Request, status

from app.core.config import get_settings
from app.models.schemas import (
    APIResponse,
    OrderSide,
    TradingViewAlert,
    TradingViewAlertConfig,
    TradingViewAlertLog,
)

logger = structlog.get_logger("jarvis.tradingview")
router = APIRouter(prefix="/tradingview", tags=["TradingView"])

_alert_configs: dict[str, TradingViewAlertConfig] = {}
_alert_logs: list[TradingViewAlertLog] = []
_MAX_LOGS = 1000


def _verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Webhook receiver ────────────────────────────────────────────────────

@router.post(
    "/webhook",
    response_model=APIResponse,
    summary="Receive TradingView webhook alerts",
)
async def receive_webhook(
    request: Request,
    x_tv_signature: str | None = Header(default=None),
) -> APIResponse:
    settings = get_settings()
    body = await request.body()

    if settings.tradingview_webhook_secret:
        if not _verify_signature(body, x_tv_signature, settings.tradingview_webhook_secret):
            logger.warning("tradingview_webhook_invalid_signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature.",
            )

    if settings.tradingview_allowed_ips:
        client_ip = request.client.host if request.client else ""
        if client_ip and client_ip not in settings.tradingview_allowed_ips:
            logger.warning(
                "tradingview_webhook_ip_blocked", ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address not allowed.",
            )

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    try:
        alert = TradingViewAlert(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid alert format: {exc}",
        )

    executed = False
    execution_result = "Alert received and logged."

    matching_config = None
    for cfg in _alert_configs.values():
        if cfg.enabled and cfg.symbol.upper() == alert.symbol.upper():
            matching_config = cfg
            break

    if matching_config and matching_config.auto_execute:
        executed = True
        execution_result = (
            f"Auto-executed {alert.action.value} {alert.volume} lots "
            f"on {alert.symbol}."
        )
        logger.info(
            "tradingview_alert_executed",
            symbol=alert.symbol,
            action=alert.action.value,
            volume=alert.volume,
        )
    else:
        logger.info(
            "tradingview_alert_received",
            symbol=alert.symbol,
            action=alert.action.value,
        )

    log_entry = TradingViewAlertLog(
        id=uuid.uuid4().hex[:12],
        alert=alert,
        executed=executed,
        execution_result=execution_result,
        received_at=datetime.now(timezone.utc),
    )
    _alert_logs.append(log_entry)
    if len(_alert_logs) > _MAX_LOGS:
        _alert_logs[:] = _alert_logs[-_MAX_LOGS:]

    return APIResponse(
        success=True,
        message=execution_result,
        data=log_entry.model_dump(mode="json"),
    )


# ── Alert configs CRUD ──────────────────────────────────────────────────

@router.get(
    "/alerts",
    response_model=APIResponse,
    summary="List all alert configurations",
)
async def list_alert_configs() -> APIResponse:
    items = list(_alert_configs.values())
    return APIResponse(
        success=True,
        data=[c.model_dump(mode="json") for c in items],
    )


@router.post(
    "/alerts",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new alert configuration",
)
async def create_alert_config(config: TradingViewAlertConfig) -> APIResponse:
    config_id = config.id or uuid.uuid4().hex[:12]
    config = config.model_copy(update={"id": config_id})
    _alert_configs[config_id] = config
    logger.info("tradingview_alert_config_created", id=config_id, name=config.name)
    return APIResponse(
        success=True,
        message="Alert configuration created.",
        data=config.model_dump(mode="json"),
    )


@router.put(
    "/alerts/{alert_id}",
    response_model=APIResponse,
    summary="Update an alert configuration",
)
async def update_alert_config(
    alert_id: str, config: TradingViewAlertConfig
) -> APIResponse:
    if alert_id not in _alert_configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert config {alert_id} not found.",
        )
    config = config.model_copy(update={"id": alert_id})
    _alert_configs[alert_id] = config
    logger.info("tradingview_alert_config_updated", id=alert_id)
    return APIResponse(
        success=True,
        message="Alert configuration updated.",
        data=config.model_dump(mode="json"),
    )


@router.delete(
    "/alerts/{alert_id}",
    response_model=APIResponse,
    summary="Delete an alert configuration",
)
async def delete_alert_config(alert_id: str) -> APIResponse:
    if alert_id not in _alert_configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert config {alert_id} not found.",
        )
    del _alert_configs[alert_id]
    logger.info("tradingview_alert_config_deleted", id=alert_id)
    return APIResponse(success=True, message="Alert configuration deleted.")


# ── Alert logs ───────────────────────────────────────────────────────────

@router.get(
    "/logs",
    response_model=APIResponse,
    summary="Get recent webhook alert logs",
)
async def get_alert_logs(
    limit: int = 50,
) -> APIResponse:
    logs = _alert_logs[-limit:][::-1]
    return APIResponse(
        success=True,
        data=[lg.model_dump(mode="json") for lg in logs],
    )
