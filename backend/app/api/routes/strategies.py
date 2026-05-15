from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.strategy import Strategy, BacktestResult, StrategyStatus, StrategyType
from app.models.user import User

router = APIRouter(prefix="/strategies", tags=["Strategies"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class StrategyRead(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    type: StrategyType
    status: StrategyStatus
    winrate: Optional[float]
    profit_factor: Optional[float]
    total_trades: int
    win_trades: int
    loss_trades: int
    total_profit: float
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    config: Optional[Dict[str, Any]]
    symbols: Optional[str]
    timeframes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    type: StrategyType
    config: Optional[Dict[str, Any]] = None
    symbols: Optional[str] = None
    timeframes: Optional[str] = None


class StrategyUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StrategyStatus] = None
    config: Optional[Dict[str, Any]] = None
    symbols: Optional[str] = None
    timeframes: Optional[str] = None


class BacktestResultRead(BaseModel):
    id: int
    strategy_id: int
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    total_trades: int
    win_trades: int
    loss_trades: int
    profit_factor: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    total_profit: float
    gross_profit: Optional[float]
    gross_loss: Optional[float]
    avg_win: Optional[float]
    avg_loss: Optional[float]
    expectancy: Optional[float]
    config: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[StrategyRead])
async def list_strategies(
    status_filter: Optional[StrategyStatus] = Query(None, alias="status"),
    type_filter: Optional[StrategyType] = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[StrategyRead]:
    stmt = select(Strategy).order_by(desc(Strategy.created_at)).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Strategy.status == status_filter)
    if type_filter:
        stmt = stmt.where(Strategy.type == type_filter)
    result = await db.execute(stmt)
    return [StrategyRead.model_validate(s) for s in result.scalars().all()]


@router.get("/{strategy_id}", response_model=StrategyRead)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StrategyRead:
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return StrategyRead.model_validate(strategy)


@router.post("/", response_model=StrategyRead, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    payload: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StrategyRead:
    existing = await db.execute(select(Strategy).where(Strategy.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Strategy '{payload.name}' already exists",
        )

    strategy = Strategy(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        type=payload.type,
        status=StrategyStatus.INACTIVE,
        config=payload.config,
        symbols=payload.symbols,
        timeframes=payload.timeframes,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return StrategyRead.model_validate(strategy)


@router.patch("/{strategy_id}", response_model=StrategyRead)
async def update_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StrategyRead:
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(strategy, field, value)

    await db.commit()
    await db.refresh(strategy)
    return StrategyRead.model_validate(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    await db.delete(strategy)
    await db.commit()


# ── Backtest results ───────────────────────────────────────────────────────────

@router.get("/{strategy_id}/backtests", response_model=List[BacktestResultRead])
async def list_backtest_results(
    strategy_id: int,
    symbol: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[BacktestResultRead]:
    stmt = (
        select(BacktestResult)
        .where(BacktestResult.strategy_id == strategy_id)
        .order_by(desc(BacktestResult.created_at))
        .limit(limit)
    )
    if symbol:
        stmt = stmt.where(BacktestResult.symbol == symbol.upper())
    result = await db.execute(stmt)
    return [BacktestResultRead.model_validate(r) for r in result.scalars().all()]
