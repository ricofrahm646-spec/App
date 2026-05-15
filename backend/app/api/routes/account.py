"""Account information routes.

Endpoints
---------
GET /info      – current account balance, equity, margin
GET /history   – historical account snapshots
GET /dashboard – aggregated dashboard data
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade import AccountSnapshot, Trade

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AccountInfoResponse(BaseModel):
    """Current account state."""

    balance: float
    equity: float
    margin: float
    free_margin: float
    drawdown: float
    open_trades: int
    timestamp: datetime


class SnapshotResponse(BaseModel):
    """Serialised account snapshot."""

    id: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    drawdown: float
    timestamp: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/info", response_model=AccountInfoResponse)
async def account_info(db: AsyncSession = Depends(get_db)) -> AccountInfoResponse:
    """Return the latest account snapshot augmented with live trade count."""
    result = await db.execute(
        select(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc()).limit(1),
    )
    snapshot = result.scalar_one_or_none()

    open_count = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "open"),
    ) or 0

    if snapshot is None:
        return AccountInfoResponse(
            balance=0.0,
            equity=0.0,
            margin=0.0,
            free_margin=0.0,
            drawdown=0.0,
            open_trades=open_count,
            timestamp=datetime.now(timezone.utc),
        )

    return AccountInfoResponse(
        balance=snapshot.balance,
        equity=snapshot.equity,
        margin=snapshot.margin,
        free_margin=snapshot.free_margin,
        drawdown=snapshot.drawdown,
        open_trades=open_count,
        timestamp=snapshot.timestamp,
    )


@router.get("/history", response_model=list[SnapshotResponse])
async def account_history(
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[AccountSnapshot]:
    """Return historical account snapshots with optional date filtering."""
    stmt = select(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc())
    if start:
        stmt = stmt.where(AccountSnapshot.timestamp >= start)
    if end:
        stmt = stmt.where(AccountSnapshot.timestamp <= end)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Aggregate key metrics into a single dashboard payload."""
    latest_snapshot = await db.scalar(
        select(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc()).limit(1),
    )

    total_trades = await db.scalar(select(func.count(Trade.id))) or 0
    open_trades = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "open"),
    ) or 0
    closed_trades = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "closed"),
    ) or 0
    total_profit = await db.scalar(
        select(func.coalesce(func.sum(Trade.profit), 0.0)).where(Trade.status == "closed"),
    )
    winning = await db.scalar(
        select(func.count(Trade.id)).where(Trade.status == "closed", Trade.profit > 0),
    ) or 0

    winrate = (winning / closed_trades * 100) if closed_trades else 0.0

    recent_result = await db.execute(
        select(AccountSnapshot)
        .order_by(AccountSnapshot.timestamp.desc())
        .limit(30),
    )
    recent_snapshots = list(recent_result.scalars().all())

    return {
        "account": {
            "balance": latest_snapshot.balance if latest_snapshot else 0.0,
            "equity": latest_snapshot.equity if latest_snapshot else 0.0,
            "drawdown": latest_snapshot.drawdown if latest_snapshot else 0.0,
        },
        "trades": {
            "total": total_trades,
            "open": open_trades,
            "closed": closed_trades,
            "winrate": round(winrate, 2),
            "total_profit": round(float(total_profit), 2),
        },
        "equity_curve": [
            {
                "timestamp": s.timestamp.isoformat(),
                "balance": s.balance,
                "equity": s.equity,
            }
            for s in reversed(recent_snapshots)
        ],
    }
