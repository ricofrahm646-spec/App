"""TradingView-style alert webhooks (JSON over HTTPS)."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class TradingViewAlert(BaseModel):
    model_config = ConfigDict(extra="allow")

    action: str | None = Field(default=None, description="buy | sell | close")
    symbol: str | None = None
    sl: float | None = None
    tp: float | None = None
    secret: str | None = None


def verify_secret(alert: TradingViewAlert, header_token: str | None) -> bool:
    expected = settings.tradingview_webhook_secret
    if not expected:
        logger.warning("TradingView webhook secret not configured — rejecting")
        return False
    return header_token == expected or alert.secret == expected
