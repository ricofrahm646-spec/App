import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.websocket import ws_manager
from app.models.trade import TradeSignal, SignalType

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class TradingViewAlert(BaseModel):
    """Payload schema sent by TradingView Pine Script alerts."""
    symbol: str
    action: str  # "buy" | "sell" | "close_buy" | "close_sell"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timeframe: Optional[str] = None
    strategy: Optional[str] = "tradingview"
    confidence: Optional[float] = None
    comment: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _verify_tradingview_signature(raw_body: bytes, provided_secret: str) -> bool:
    """Verify the shared secret sent in the TradingView payload.

    TradingView does not support HMAC; instead we compare a plain-text
    secret token embedded in the JSON body.
    """
    expected = settings.TRADINGVIEW_WEBHOOK_SECRET
    if not expected:
        return True  # secret verification disabled – dev mode
    return hmac.compare_digest(provided_secret.encode(), expected.encode())


_ACTION_MAP: Dict[str, SignalType] = {
    "buy": SignalType.BUY,
    "sell": SignalType.SELL,
    "close_buy": SignalType.CLOSE_BUY,
    "close_sell": SignalType.CLOSE_SELL,
    "hold": SignalType.HOLD,
}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/tradingview", status_code=status.HTTP_200_OK)
async def tradingview_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Receive and process TradingView Pine Script alert webhooks."""
    try:
        body_bytes = await request.body()
        body: Dict[str, Any] = json.loads(body_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning(f"TradingView webhook – invalid JSON: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc

    # Verify secret token if configured
    provided_secret = body.pop("secret", "")
    if not _verify_tradingview_signature(body_bytes, str(provided_secret)):
        logger.warning("TradingView webhook – invalid secret token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret"
        )

    try:
        alert = TradingViewAlert(**body)
    except Exception as exc:
        logger.warning(f"TradingView webhook – schema error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Payload validation error: {exc}",
        ) from exc

    signal_type = _ACTION_MAP.get(alert.action.lower(), SignalType.HOLD)

    signal = TradeSignal(
        symbol=alert.symbol.upper(),
        strategy_name=alert.strategy or "tradingview",
        signal_type=signal_type,
        price=alert.price,
        stop_loss=alert.stop_loss,
        take_profit=alert.take_profit,
        confidence=alert.confidence,
        timeframe=alert.timeframe,
        executed=False,
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)

    logger.info(
        f"TradingView webhook processed: symbol={alert.symbol} "
        f"action={alert.action} signal_id={signal.id}"
    )

    # Push signal to all connected WebSocket clients
    await ws_manager.broadcast(
        {
            "type": "trade_signal",
            "signal_id": signal.id,
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "price": signal.price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "confidence": signal.confidence,
            "strategy": signal.strategy_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        topic="signals",
    )

    return {"status": "ok", "signal_id": signal.id, "signal_type": signal_type}
