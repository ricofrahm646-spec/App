"""Trade management routes.

Endpoints
---------
GET    /                – list trades (with optional filters)
POST   /open            – open a new trade
POST   /{trade_id}/close – close an existing trade
GET    /stats           – aggregated trade statistics
GET    /open            – currently open trades
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade import Trade

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TradeOpenRequest(BaseModel):
    """Payload for opening a new trade."""

    symbol: str = Field(..., examples=["EURUSD"])
    direction: str = Field(..., pattern="^(buy|sell)$", examples=["buy"])
    volume: float = Field(..., gt=0, examples=[0.1])
    open_price: float = Field(..., gt=0)
    sl: Optional[float] = None
    tp: Optional[float] = None
    strategy_name: Optional[str] = None


class TradeCloseRequest(BaseModel):
    """Payload for closing a trade."""

    close_price: float = Field(..., gt=0)
    profit: Optional[float] = None


class TradeResponse(BaseModel):
    """Serialised trade returned to the client."""

    id: int
    symbol: str
    direction: str
    volume: float
    open_price: float
    close_price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    open_time: datetime
    close_time: Optional[datetime] = None
    profit: Optional[float] = None
    status: str
    strategy_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TradeResponse])
async def list_trades(
    symbol: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Trade]:
    """Return a paginated, filtered list of trades."""
    stmt = select(Trade).order_by(Trade.open_time.desc())
    if symbol:
        stmt = stmt.where(Trade.symbol == symbol.upper())
    if status:
        stmt = stmt.where(Trade.status == status)
    if strategy:
        stmt = stmt.where(Trade.strategy_name == strategy)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/open", response_model=TradeResponse, status_code=201)
async def open_trade(
    payload: TradeOpenRequest,
    db: AsyncSession = Depends(get_db),
) -> Trade:
    """Record a new trade."""
    trade = Trade(
        symbol=payload.symbol.upper(),
        direction=payload.direction,
        volume=payload.volume,
        open_price=payload.open_price,
        sl=payload.sl,
        tp=payload.tp,
        strategy_name=payload.strategy_name,
        status="open",
        open_time=datetime.now(timezone.utc),
    )
    db.add(trade)
    await db.flush()
    await db.refresh(trade)
    return trade


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: int,
    payload: TradeCloseRequest,
    db: AsyncSession = Depends(get_db),
) -> Trade:
    """Close an open trade by ID."""
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail="Trade is not open")

    trade.close_price = payload.close_price
    trade.profit = payload.profit
    trade.close_time = datetime.now(timezone.utc)
    trade.status = "closed"
    await db.flush()
    await db.refresh(trade)
    return trade


@router.get("/stats")
async def trade_stats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return aggregated trade statistics."""
    total = await db.scalar(select(func.count(Trade.id)))
    closed = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "closed"),
    )
    winning = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "closed", Trade.profit > 0),
    )
    total_profit = await db.scalar(
        select(func.coalesce(func.sum(Trade.profit), 0.0)).where(Trade.status == "closed"),
    )
    avg_profit = await db.scalar(
        select(func.coalesce(func.avg(Trade.profit), 0.0)).where(Trade.status == "closed"),
    )

    winrate = (winning / closed * 100) if closed else 0.0
    return {
        "total_trades": total or 0,
        "closed_trades": closed or 0,
        "winning_trades": winning or 0,
        "winrate": round(winrate, 2),
        "total_profit": round(float(total_profit), 2),
        "average_profit": round(float(avg_profit), 2),
    }


@router.get("/open", response_model=list[TradeResponse])
async def open_trades(db: AsyncSession = Depends(get_db)) -> list[Trade]:
    """Return all currently open trades."""
    result = await db.execute(
        select(Trade).where(Trade.status == "open").order_by(Trade.open_time.desc()),
    )
    return list(result.scalars().all())
