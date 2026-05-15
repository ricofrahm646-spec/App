from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.trade import Trade, TradeSignal, TradeStatus, OrderType, SignalType
from app.models.user import User

router = APIRouter(prefix="/trades", tags=["Trades"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class TradeRead(BaseModel):
    id: int
    ticket: Optional[int]
    symbol: str
    order_type: OrderType
    lot_size: float
    open_price: Optional[float]
    close_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    profit_loss: Optional[float]
    status: TradeStatus
    strategy_name: Optional[str]
    magic_number: Optional[int]
    comment: Optional[str]
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeCreate(BaseModel):
    symbol: str
    order_type: OrderType
    lot_size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: Optional[str] = None
    comment: Optional[str] = None
    magic_number: Optional[int] = None


class TradeUpdate(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = None


class TradeSignalRead(BaseModel):
    id: int
    symbol: str
    strategy_name: str
    signal_type: SignalType
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: Optional[float]
    timeframe: Optional[str]
    executed: bool
    trade_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeSummary(BaseModel):
    total_trades: int
    open_trades: int
    closed_trades: int
    total_profit: float
    win_trades: int
    loss_trades: int
    winrate: float


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[TradeRead])
async def list_trades(
    symbol: Optional[str] = Query(None),
    status_filter: Optional[TradeStatus] = Query(None, alias="status"),
    strategy_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[TradeRead]:
    stmt = select(Trade).order_by(desc(Trade.created_at)).limit(limit).offset(offset)
    if symbol:
        stmt = stmt.where(Trade.symbol == symbol.upper())
    if status_filter:
        stmt = stmt.where(Trade.status == status_filter)
    if strategy_name:
        stmt = stmt.where(Trade.strategy_name == strategy_name)
    result = await db.execute(stmt)
    trades = result.scalars().all()
    return [TradeRead.model_validate(t) for t in trades]


@router.get("/summary", response_model=TradeSummary)
async def get_trade_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TradeSummary:
    result = await db.execute(select(Trade))
    trades = result.scalars().all()

    total = len(trades)
    open_t = sum(1 for t in trades if t.status == TradeStatus.OPEN)
    closed_t = sum(1 for t in trades if t.status == TradeStatus.CLOSED)
    wins = sum(1 for t in trades if t.profit_loss is not None and t.profit_loss > 0)
    losses = sum(1 for t in trades if t.profit_loss is not None and t.profit_loss <= 0)
    total_profit = sum(t.profit_loss for t in trades if t.profit_loss is not None)
    winrate = (wins / closed_t * 100) if closed_t > 0 else 0.0

    return TradeSummary(
        total_trades=total,
        open_trades=open_t,
        closed_trades=closed_t,
        total_profit=total_profit,
        win_trades=wins,
        loss_trades=losses,
        winrate=winrate,
    )


@router.get("/{trade_id}", response_model=TradeRead)
async def get_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TradeRead:
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return TradeRead.model_validate(trade)


@router.post("/", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
async def create_trade(
    payload: TradeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TradeRead:
    trade = Trade(
        symbol=payload.symbol.upper(),
        order_type=payload.order_type,
        lot_size=payload.lot_size,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        strategy_name=payload.strategy_name,
        comment=payload.comment,
        magic_number=payload.magic_number,
        status=TradeStatus.PENDING,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return TradeRead.model_validate(trade)


@router.patch("/{trade_id}", response_model=TradeRead)
async def update_trade(
    trade_id: int,
    payload: TradeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TradeRead:
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(trade, field, value)

    await db.commit()
    await db.refresh(trade)
    return TradeRead.model_validate(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    await db.delete(trade)
    await db.commit()


# ── Signals ────────────────────────────────────────────────────────────────────

@router.get("/signals/", response_model=List[TradeSignalRead])
async def list_signals(
    symbol: Optional[str] = Query(None),
    executed: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[TradeSignalRead]:
    stmt = select(TradeSignal).order_by(desc(TradeSignal.created_at)).limit(limit)
    if symbol:
        stmt = stmt.where(TradeSignal.symbol == symbol.upper())
    if executed is not None:
        stmt = stmt.where(TradeSignal.executed == executed)
    result = await db.execute(stmt)
    return [TradeSignalRead.model_validate(s) for s in result.scalars().all()]
