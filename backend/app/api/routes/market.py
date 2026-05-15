from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.market import MarketData, AIAnalysis, MarketPhase, AISignal
from app.models.user import User

router = APIRouter(prefix="/market", tags=["Market Data"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CandleRead(BaseModel):
    id: int
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: Optional[float]
    timestamp: datetime

    model_config = {"from_attributes": True}


class AIAnalysisRead(BaseModel):
    id: int
    symbol: str
    timeframe: Optional[str]
    model_name: Optional[str]
    market_phase: MarketPhase
    signal: AISignal
    confidence: Optional[float]
    predicted_direction: Optional[float]
    price_at_analysis: Optional[float]
    indicators: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class TickerSummary(BaseModel):
    symbol: str
    timeframe: str
    last_close: float
    last_timestamp: datetime
    candle_count: int
    latest_signal: Optional[AISignal]
    latest_phase: Optional[MarketPhase]
    latest_confidence: Optional[float]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/candles", response_model=List[CandleRead])
async def get_candles(
    symbol: str = Query(..., description="Trading symbol e.g. EURUSD"),
    timeframe: str = Query("H1", description="Timeframe e.g. M15, H1, H4, D1"),
    limit: int = Query(200, ge=1, le=5000),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[CandleRead]:
    stmt = (
        select(MarketData)
        .where(
            MarketData.symbol == symbol.upper(),
            MarketData.timeframe == timeframe.upper(),
        )
        .order_by(desc(MarketData.timestamp))
        .limit(limit)
    )
    if from_date:
        stmt = stmt.where(MarketData.timestamp >= from_date)
    if to_date:
        stmt = stmt.where(MarketData.timestamp <= to_date)

    result = await db.execute(stmt)
    candles = result.scalars().all()
    return [CandleRead.model_validate(c) for c in reversed(candles)]


@router.get("/analysis", response_model=List[AIAnalysisRead])
async def get_ai_analysis(
    symbol: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[AIAnalysisRead]:
    stmt = select(AIAnalysis).order_by(desc(AIAnalysis.created_at)).limit(limit)
    if symbol:
        stmt = stmt.where(AIAnalysis.symbol == symbol.upper())
    result = await db.execute(stmt)
    return [AIAnalysisRead.model_validate(a) for a in result.scalars().all()]


@router.get("/analysis/latest/{symbol}", response_model=AIAnalysisRead)
async def get_latest_analysis(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AIAnalysisRead:
    result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.symbol == symbol.upper())
        .order_by(desc(AIAnalysis.created_at))
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI analysis found for {symbol}",
        )
    return AIAnalysisRead.model_validate(analysis)


@router.get("/symbols", response_model=List[str])
async def list_available_symbols(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[str]:
    """Return distinct symbols that have market data in the database."""
    from sqlalchemy import distinct
    result = await db.execute(select(distinct(MarketData.symbol)).order_by(MarketData.symbol))
    return list(result.scalars().all())


@router.get("/ticker/{symbol}", response_model=TickerSummary)
async def get_ticker_summary(
    symbol: str,
    timeframe: str = Query("H1"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TickerSummary:
    sym = symbol.upper()
    tf = timeframe.upper()

    candle_result = await db.execute(
        select(MarketData)
        .where(MarketData.symbol == sym, MarketData.timeframe == tf)
        .order_by(desc(MarketData.timestamp))
        .limit(1)
    )
    latest_candle = candle_result.scalar_one_or_none()
    if latest_candle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for {sym}/{tf}",
        )

    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count(MarketData.id)).where(
            MarketData.symbol == sym, MarketData.timeframe == tf
        )
    )
    candle_count = count_result.scalar() or 0

    analysis_result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.symbol == sym)
        .order_by(desc(AIAnalysis.created_at))
        .limit(1)
    )
    latest_analysis = analysis_result.scalar_one_or_none()

    return TickerSummary(
        symbol=sym,
        timeframe=tf,
        last_close=latest_candle.close,
        last_timestamp=latest_candle.timestamp,
        candle_count=candle_count,
        latest_signal=latest_analysis.signal if latest_analysis else None,
        latest_phase=latest_analysis.market_phase if latest_analysis else None,
        latest_confidence=latest_analysis.confidence if latest_analysis else None,
    )
