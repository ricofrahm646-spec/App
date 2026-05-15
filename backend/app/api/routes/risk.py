"""
Risk Router - real-time risk metrics, lot sizing, trade validation, drawdown, emergency stop.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_mt5
from app.database import get_db
from app.services.mt5_service import MT5Service
from app.services.risk_service import RiskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["risk"])


# ─────────────────────────────────────── Request models ─────────────────────

class CalculateLotRequest(BaseModel):
    account_balance: Optional[float] = Field(None, description="Override account balance")
    risk_percent: Optional[float] = Field(None, gt=0, le=50)
    stop_loss_pips: float = Field(..., gt=0)
    pip_value: float = Field(1.0, gt=0)
    lot_step: float = Field(0.01, gt=0)
    min_lot: float = Field(0.01, gt=0)
    max_lot: float = Field(100.0, gt=0)


class ValidateTradeRequest(BaseModel):
    symbol: str = Field(...)
    order_type: str = Field(..., description="BUY or SELL")
    lot_size: float = Field(..., gt=0)
    stop_loss: float = Field(0.0, ge=0)
    take_profit: float = Field(0.0, ge=0)


class UpdateRiskSettingsRequest(BaseModel):
    risk_percent_per_trade: Optional[float] = Field(None, gt=0, le=50)
    max_daily_loss_percent: Optional[float] = Field(None, gt=0, le=100)
    max_drawdown_percent: Optional[float] = Field(None, gt=0, le=100)
    max_open_trades: Optional[int] = Field(None, ge=1, le=100)
    max_lot_size: Optional[float] = Field(None, gt=0)
    min_lot_size: Optional[float] = Field(None, gt=0)
    max_spread_points: Optional[int] = Field(None, ge=0)
    allow_hedging: Optional[bool] = None


class EmergencyStopRequest(BaseModel):
    reason: str = Field("Manual trigger")
    close_all_positions: bool = Field(False)


class ReleaseStopRequest(BaseModel):
    confirm: bool = Field(...)


# ─────────────────────────────────────────────────────── Endpoints ───────────

@router.get("/metrics", summary="Current risk metrics")
async def get_metrics(
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Return a comprehensive real-time risk snapshot including exposure,
    drawdown, daily P&L, limit breach flags, and emergency stop status.
    """
    try:
        account = await mt5.get_account_info()
    except Exception:
        account = {"balance": 0, "equity": 0}

    try:
        positions = await mt5.get_open_trades()
    except Exception:
        positions = []

    try:
        history = await mt5.get_trade_history(days=30)
    except Exception:
        history = []

    return RiskService.get_metrics(
        db,
        account_balance=account.get("balance", 0),
        account_equity=account.get("equity", 0),
        open_positions=positions,
        trade_history=history,
    )


@router.post("/calculate/lot", summary="Calculate optimal lot size")
async def calculate_lot(
    req: CalculateLotRequest,
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Calculate the appropriate lot size to risk the specified % of the account
    given a stop loss distance in pips.
    """
    balance = req.account_balance
    if balance is None:
        try:
            account = await mt5.get_account_info()
            balance = account.get("balance", 0)
        except Exception:
            balance = 0

    risk_pct = req.risk_percent
    if risk_pct is None:
        s = RiskService.get_settings(db)
        risk_pct = s.risk_percent_per_trade

    if balance <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Account balance is 0 or MT5 not connected. Provide account_balance explicitly.",
        )

    return RiskService.calculate_lot_size(
        account_balance=balance,
        risk_percent=risk_pct,
        stop_loss_pips=req.stop_loss_pips,
        pip_value=req.pip_value,
        lot_step=req.lot_step,
        min_lot=req.min_lot,
        max_lot=req.max_lot,
    )


@router.post("/validate/trade", summary="Validate a trade before placing")
async def validate_trade(
    req: ValidateTradeRequest,
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Pre-flight check for a proposed trade against risk settings,
    position limits, and emergency stop.
    Returns {"allowed": bool, "reason": str}.
    """
    if req.order_type.upper() not in ("BUY", "SELL"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="order_type must be BUY or SELL")

    try:
        account = await mt5.get_account_info()
    except Exception:
        account = {"balance": 0, "equity": 0, "margin_level": 9999}

    try:
        open_trades = await mt5.get_open_trades()
    except Exception:
        open_trades = []

    return RiskService.validate_trade(
        symbol=req.symbol,
        direction=req.order_type.upper(),
        account_info=account,
        open_trades=open_trades,
        db=db,
    )


@router.get("/drawdown", summary="Drawdown analysis")
async def get_drawdown(
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Return current and historical drawdown metrics."""
    try:
        account = await mt5.get_account_info()
        balance = account.get("balance", 0)
        equity = account.get("equity", 0)
    except Exception:
        balance = equity = 0

    try:
        history = await mt5.get_trade_history(days=90)
    except Exception:
        history = []

    return RiskService.get_drawdown_info(balance, equity, history)


@router.get("/settings", summary="Current risk settings")
def get_settings(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return the current risk management configuration."""
    s = RiskService.get_settings(db)
    return {
        "id": s.id,
        "risk_percent_per_trade": s.risk_percent_per_trade,
        "max_daily_loss_percent": s.max_daily_loss_percent,
        "max_drawdown_percent": s.max_drawdown_percent,
        "max_open_trades": s.max_open_trades,
        "max_lot_size": s.max_lot_size,
        "min_lot_size": s.min_lot_size,
        "max_spread_points": s.max_spread_points,
        "allow_hedging": s.allow_hedging,
        "emergency_stop_enabled": s.emergency_stop_enabled,
        "emergency_stopped_at": s.emergency_stopped_at.isoformat() if s.emergency_stopped_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.put("/settings", summary="Update risk settings")
def update_settings(req: UpdateRiskSettingsRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Update any combination of risk management parameters."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields provided to update")
    s = RiskService.update_settings(db, updates)
    return {
        "updated": True,
        "risk_percent_per_trade": s.risk_percent_per_trade,
        "max_daily_loss_percent": s.max_daily_loss_percent,
        "max_drawdown_percent": s.max_drawdown_percent,
        "max_open_trades": s.max_open_trades,
        "max_lot_size": s.max_lot_size,
        "min_lot_size": s.min_lot_size,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.post("/emergency-stop", summary="Trigger emergency stop – halt all trading")
async def trigger_emergency_stop(
    req: EmergencyStopRequest,
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Immediately halt all new trade placement by enabling the emergency stop flag.
    Optionally closes all open positions.
    """
    result = RiskService.trigger_emergency_stop(db, req.reason)

    if req.close_all_positions:
        try:
            closed = await mt5.close_all_orders()
            result["positions_closed"] = closed
        except Exception as exc:
            result["close_error"] = str(exc)

    return result


@router.post("/emergency-stop/release", summary="Release emergency stop – resume trading")
def release_emergency_stop(req: ReleaseStopRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Release the emergency stop. Requires explicit confirmation (confirm=true)."""
    if not req.confirm:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Set confirm=true to release the emergency stop",
        )
    return RiskService.release_emergency_stop(db)
