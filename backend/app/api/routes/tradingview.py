"""
TradingView Router - inbound webhook alerts, signal management, Pine Script generation.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_mt5, get_tv
from app.database import get_db
from app.models.tradingview_model import TradingViewConfig, TradingViewSignal
from app.services.mt5_service import MT5Service
from app.services.tradingview_service import TradingViewService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tradingview", tags=["tradingview"])


# ─────────────────────────────────────── Request models ─────────────────────

class ConfigureWebhookRequest(BaseModel):
    webhook_secret: str = Field(..., min_length=8)
    auto_trade: bool = Field(False)
    default_lot_size: float = Field(0.01, gt=0)
    default_magic: int = Field(99001)


class GeneratePineScriptRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(...)
    strategy_type: Optional[str] = Field("trend", description="trend, mean-reversion, breakout")
    timeframe: Optional[str] = Field("60")
    risk_percent: float = Field(2.0)
    long_only: bool = Field(False)


def _get_db_config(db: Session) -> Optional[TradingViewConfig]:
    return db.query(TradingViewConfig).filter(TradingViewConfig.is_active == True).first()  # noqa: E712


def _persist_signal(db: Session, signal: Dict) -> TradingViewSignal:
    record = TradingViewSignal(
        ticker=signal.get("symbol", "UNKNOWN"),
        action=signal.get("action", "BUY").upper(),
        price=signal.get("price"),
        quantity=signal.get("volume"),
        stop_loss=signal.get("sl"),
        take_profit=signal.get("tp"),
        comment=signal.get("comment", "TradingView Signal"),
        raw_payload=signal,
        processed=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ─────────────────────────────────────────────────────── Endpoints ───────────

@router.post("/webhook", summary="Receive TradingView alert webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    tv: TradingViewService = Depends(get_tv),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Endpoint that TradingView posts alert payloads to.

    Expected JSON payload:
    ```json
    {
      "symbol": "EURUSD",
      "action": "BUY",
      "price": 1.08500,
      "sl": 1.08200,
      "tp": 1.09000,
      "volume": 0.10
    }
    ```
    """
    config = _get_db_config(db)
    secret = config.webhook_secret if config else ""

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON payload")

    try:
        signal = await tv.process_webhook(payload, secret)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db_signal = _persist_signal(db, signal)
    trade_result = None
    error = None

    # Auto-execute trade if MT5 is available
    action = signal.get("action", "").upper()
    if action in ("BUY", "SELL") and await mt5.is_connected():
        try:
            from app.services.risk_service import RiskService
            risk = RiskService.get_settings(db)
            if not risk.emergency_stop_enabled:
                trade_result = await mt5.place_order(
                    symbol=signal["symbol"],
                    order_type=action,
                    lot_size=signal.get("volume") or 0.01,
                    sl=signal.get("sl", 0.0),
                    tp=signal.get("tp", 0.0),
                    comment=f"TV:{signal.get('strategy', 'Alert')}",
                    magic=99001,
                )
                db_signal.processed = True
                db_signal.trade_ticket = trade_result.get("ticket") if isinstance(trade_result, dict) else None
                db.commit()
        except Exception as exc:
            error = str(exc)
            db_signal.error = error
            db.commit()
            logger.error("Auto-trade failed for TV signal #%d: %s", db_signal.id, exc)

    return {
        "received": True,
        "signal_id": db_signal.id,
        "symbol": signal.get("symbol"),
        "action": signal.get("action"),
        "auto_traded": trade_result is not None,
        "trade_result": trade_result,
        "error": error,
    }


@router.get("/signals", summary="List received TradingView signals")
def get_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    processed: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all received TradingView signals."""
    q = db.query(TradingViewSignal).order_by(TradingViewSignal.created_at.desc())
    if processed is not None:
        q = q.filter(TradingViewSignal.processed == processed)
    signals = q.offset(skip).limit(limit).all()
    return [
        {
            "id": s.id,
            "ticker": s.ticker,
            "action": s.action,
            "price": s.price,
            "quantity": s.quantity,
            "stop_loss": s.stop_loss,
            "take_profit": s.take_profit,
            "processed": s.processed,
            "trade_ticket": s.trade_ticket,
            "error": s.error,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


@router.post("/generate/pinescript", summary="Generate Pine Script indicator/strategy")
async def generate_pinescript(
    req: GeneratePineScriptRequest,
    tv: TradingViewService = Depends(get_tv),
) -> Dict[str, Any]:
    """Generate a Pine Script v5 strategy from a template or AI-augmented."""
    try:
        params = {
            "strategy_type": req.strategy_type or "trend",
            "timeframe": req.timeframe or "60",
            "risk_percent": req.risk_percent,
            "long_only": req.long_only,
            "extra": req.description,
        }
        code = await tv.generate_pine_script(req.name, params)
        return {"name": req.name, "code": code, "type": "PineScript"}
    except Exception as exc:
        logger.exception("Pine Script generation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/status", summary="TradingView webhook status")
def get_status(db: Session = Depends(get_db), tv: TradingViewService = Depends(get_tv)) -> Dict[str, Any]:
    """Return webhook configuration status and signal counts."""
    config = _get_db_config(db)
    total = db.query(TradingViewSignal).count()
    pending = db.query(TradingViewSignal).filter(TradingViewSignal.processed == False).count()  # noqa: E712
    return {
        "configured": config is not None,
        "webhook_secret_set": bool(config and config.webhook_secret),
        "total_signals": total,
        "pending_signals": pending,
        "in_memory_signals": len(tv._signal_history),
        "webhook_url": "/api/tradingview/webhook",
    }


@router.post("/configure", summary="Configure webhook secret")
def configure(req: ConfigureWebhookRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Set the shared webhook secret for TradingView alert verification."""
    from datetime import datetime
    existing = db.query(TradingViewConfig).first()
    if existing:
        existing.webhook_secret = req.webhook_secret
        existing.updated_at = datetime.utcnow()
        db.commit()
    else:
        config = TradingViewConfig(webhook_secret=req.webhook_secret, is_active=True)
        db.add(config)
        db.commit()
    return {
        "configured": True,
        "webhook_url": "/api/tradingview/webhook",
        "auto_trade": req.auto_trade,
        "default_lot_size": req.default_lot_size,
        "message": "TradingView webhook configured. Add the URL to your TradingView alert.",
    }
