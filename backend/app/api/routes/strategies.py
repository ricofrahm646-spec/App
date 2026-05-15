"""Strategy management routes.

Endpoints
---------
GET    /                     – list strategies
POST   /                     – create a strategy
PUT    /{strategy_id}        – update a strategy
DELETE /{strategy_id}        – deactivate a strategy
POST   /{strategy_id}/backtest   – run a backtest
GET    /{strategy_id}/performance – strategy performance stats
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade import Strategy, Trade

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class StrategyCreate(BaseModel):
    """Payload for creating a new strategy."""

    name: str = Field(..., max_length=128)
    type: str = Field(..., max_length=64, examples=["trend_following"])
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    is_active: bool = True


class StrategyUpdate(BaseModel):
    """Payload for updating an existing strategy."""

    name: Optional[str] = Field(None, max_length=128)
    type: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class StrategyResponse(BaseModel):
    """Serialised strategy returned to the client."""

    id: int
    name: str
    type: str
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    is_active: bool
    winrate: float
    profit_factor: float
    total_trades: int
    created_at: datetime

    class Config:
        from_attributes = True


class BacktestRequest(BaseModel):
    """Parameters for running a backtest."""

    symbol: str = Field(..., examples=["EURUSD"])
    timeframe: str = Field(..., examples=["H1"])
    start_date: datetime
    end_date: datetime
    initial_balance: float = Field(10_000.0, gt=0)


class BacktestResult(BaseModel):
    """Summary result of a backtest run."""

    strategy_id: int
    symbol: str
    timeframe: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    winrate: float
    profit_factor: float
    net_profit: float
    max_drawdown: float
    sharpe_ratio: float
    start_date: datetime
    end_date: datetime


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(db: AsyncSession = Depends(get_db)) -> list[Strategy]:
    """Return all strategies."""
    result = await db.execute(select(Strategy).order_by(Strategy.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    payload: StrategyCreate,
    db: AsyncSession = Depends(get_db),
) -> Strategy:
    """Create a new strategy."""
    existing = await db.execute(select(Strategy).where(Strategy.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Strategy name already exists")

    strategy = Strategy(
        name=payload.name,
        type=payload.type,
        description=payload.description,
        parameters=payload.parameters,
        is_active=payload.is_active,
    )
    db.add(strategy)
    await db.flush()
    await db.refresh(strategy)
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
) -> Strategy:
    """Update fields on an existing strategy."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(strategy, field, value)

    await db.flush()
    await db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
) -> Strategy:
    """Soft-delete: mark a strategy as inactive."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy.is_active = False
    await db.flush()
    await db.refresh(strategy)
    return strategy


@router.post("/{strategy_id}/backtest", response_model=BacktestResult)
async def run_backtest(
    strategy_id: int,
    payload: BacktestRequest,
    db: AsyncSession = Depends(get_db),
) -> BacktestResult:
    """Run a backtest for a given strategy over a date range.

    Currently returns a placeholder result.  Integrate a real backtesting
    engine (backtrader / vectorbt) in production.
    """
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Placeholder – replace with actual backtesting logic
    return BacktestResult(
        strategy_id=strategy.id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        winrate=0.0,
        profit_factor=0.0,
        net_profit=0.0,
        max_drawdown=0.0,
        sharpe_ratio=0.0,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )


@router.get("/{strategy_id}/performance")
async def strategy_performance(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return detailed performance metrics for a strategy."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    closed_trades_q = select(Trade).where(
        Trade.strategy_id == strategy_id,
        Trade.status == "closed",
    )
    closed_result = await db.execute(closed_trades_q)
    closed_trades = list(closed_result.scalars().all())

    total = len(closed_trades)
    winners = [t for t in closed_trades if (t.profit or 0) > 0]
    losers = [t for t in closed_trades if (t.profit or 0) <= 0]

    gross_profit = sum(t.profit for t in winners if t.profit)
    gross_loss = abs(sum(t.profit for t in losers if t.profit))
    profit_factor = (gross_profit / gross_loss) if gross_loss else 0.0
    winrate = (len(winners) / total * 100) if total else 0.0

    return {
        "strategy_id": strategy.id,
        "strategy_name": strategy.name,
        "total_trades": total,
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "winrate": round(winrate, 2),
        "profit_factor": round(profit_factor, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_profit": round(gross_profit - gross_loss, 2),
    }
