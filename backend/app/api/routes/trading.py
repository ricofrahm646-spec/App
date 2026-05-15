"""
Trading Router - MT5 account, positions, orders, symbols.
All operations are proxied through the async MT5Service.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_mt5
from app.core.config import settings
from app.database import get_db
from app.services.mt5_service import MT5Service
from app.services.risk_service import RiskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["trading"])


# ─────────────────────────────────────── Request / Response models ────────────

class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol, e.g. EURUSD")
    order_type: str = Field(..., description="BUY or SELL")
    lot_size: float = Field(..., gt=0, description="Trade volume in lots")
    stop_loss: float = Field(0.0, ge=0, description="Stop loss price (0 = no SL)")
    take_profit: float = Field(0.0, ge=0, description="Take profit price (0 = no TP)")
    comment: Optional[str] = Field("JARVIS", description="Trade comment")
    magic_number: int = Field(12345, description="Magic number for EA identification")
    price: Optional[float] = Field(None, description="Limit price (None = market order)")


class ModifyOrderRequest(BaseModel):
    stop_loss: float = Field(..., ge=0, description="New stop loss price")
    take_profit: float = Field(..., ge=0, description="New take profit price")


class MT5ConnectRequest(BaseModel):
    login: int = Field(..., description="MT5 account login number")
    password: str = Field(..., description="MT5 account password")
    server: str = Field(..., description="MT5 broker server name")


# ─────────────────────────────────────────────────────── Endpoints ────────────

@router.get("/status", summary="MT5 connection status")
async def get_status(mt5: MT5Service = Depends(get_mt5)) -> Dict[str, Any]:
    """Return current MT5 terminal connection status."""
    connected = await mt5.is_connected()
    return {
        "connected": connected,
        "mt5_available": mt5._connected,
    }


@router.post("/connect", summary="Connect to MT5")
async def connect_mt5(
    req: MT5ConnectRequest,
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Connect to MetaTrader 5 with the provided credentials."""
    success = await mt5.connect(
        login=req.login,
        password=req.password,
        server=req.server,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to MT5. Check credentials and server.",
        )
    account = await mt5.get_account_info()
    return {"success": True, "message": "Connected to MT5", "account": account}


@router.post("/disconnect", summary="Disconnect from MT5")
async def disconnect_mt5(mt5: MT5Service = Depends(get_mt5)) -> Dict[str, Any]:
    """Gracefully shut down the MT5 connection."""
    await mt5.disconnect()
    return {"success": True, "message": "Disconnected from MT5"}


@router.get("/account", summary="Account information")
async def get_account(mt5: MT5Service = Depends(get_mt5)) -> Dict[str, Any]:
    """Retrieve live account details: balance, equity, margin, leverage, etc."""
    try:
        return await mt5.get_account_info()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/positions", summary="Open positions")
async def get_positions(
    mt5: MT5Service = Depends(get_mt5),
) -> List[Dict[str, Any]]:
    """Return all currently open MT5 positions."""
    try:
        return await mt5.get_open_trades()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/history", summary="Trade history")
async def get_history(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    mt5: MT5Service = Depends(get_mt5),
) -> List[Dict[str, Any]]:
    """Return closed deals from the past N days."""
    try:
        return await mt5.get_trade_history(days=days)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/order", summary="Place new market/limit order", status_code=status.HTTP_201_CREATED)
async def place_order(
    req: PlaceOrderRequest,
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Send a new order to MT5. Validates against risk settings before sending.
    """
    if req.order_type.upper() not in ("BUY", "SELL"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="order_type must be BUY or SELL",
        )

    risk_settings = RiskService.get_settings(db)
    if risk_settings.emergency_stop_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Emergency stop is active. Trading is halted.",
        )
    if req.lot_size > risk_settings.max_lot_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Lot size {req.lot_size} exceeds maximum allowed {risk_settings.max_lot_size}",
        )

    try:
        result = await mt5.place_order(
            symbol=req.symbol,
            order_type=req.order_type,
            lot_size=req.lot_size,
            sl=req.stop_loss,
            tp=req.take_profit,
            comment=req.comment or "JARVIS",
            magic=req.magic_number,
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order placement failed")
        return result if isinstance(result, dict) else {"success": True, "result": result}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/order/{ticket}", summary="Close a specific position")
async def close_order(
    ticket: int,
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Close the position identified by the given ticket number."""
    try:
        success = await mt5.close_order(ticket)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to close position #{ticket}")
        return {"success": True, "ticket": ticket, "message": "Position closed"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/orders/all", summary="Close all open positions")
async def close_all_orders(mt5: MT5Service = Depends(get_mt5)) -> Dict[str, Any]:
    """Close every open MT5 position."""
    try:
        success = await mt5.close_all_orders()
        return {"success": success, "message": "All positions closed" if success else "Some positions could not be closed"}
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.put("/order/{ticket}", summary="Modify SL/TP of an open position")
async def modify_order(
    ticket: int,
    req: ModifyOrderRequest,
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Update the stop loss and take profit of an existing position."""
    try:
        success = await mt5.modify_order(ticket, req.stop_loss, req.take_profit)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modify failed")
        return {"success": True, "ticket": ticket, "stop_loss": req.stop_loss, "take_profit": req.take_profit}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/symbol/{symbol}", summary="Symbol information")
async def get_symbol_info(
    symbol: str,
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Return detailed specification of a trading symbol."""
    try:
        return await mt5.get_symbol_info(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/price/{symbol}", summary="Current bid/ask price")
async def get_price(
    symbol: str,
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Return the latest tick (bid, ask, time) for a symbol."""
    try:
        return await mt5.get_current_price(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/charts", summary="Active MT5 charts")
async def get_charts(mt5: MT5Service = Depends(get_mt5)) -> List[Dict[str, Any]]:
    """Return a list of visible symbols/charts in the MT5 terminal."""
    try:
        return await mt5.get_active_charts()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
