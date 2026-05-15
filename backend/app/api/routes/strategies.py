"""Strategy registry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from backend.app.db.models import Strategy
from backend.app.db.session import get_session
from backend.app.schemas.common import StrategyView
from strategies.registry import list_kinds

router = APIRouter()


@router.get("/kinds")
async def kinds() -> list[str]:
    return list_kinds()


@router.get("", response_model=list[StrategyView])
async def list_strategies(session: AsyncSession = Depends(get_session)) -> list[StrategyView]:
    rows = await session.scalars(select(Strategy).order_by(Strategy.id))
    return [
        StrategyView(
            id=s.id,
            name=s.name,
            kind=s.kind,
            symbol=s.symbol,
            timeframe=s.timeframe,
            parameters=s.parameters or {},
            enabled=s.enabled,
            score=s.score,
            notes=s.notes,
        )
        for s in rows
    ]


@router.post("", response_model=StrategyView)
async def create_strategy(
    payload: StrategyView, session: AsyncSession = Depends(get_session)
) -> StrategyView:
    strat = Strategy(
        name=payload.name,
        kind=payload.kind,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        parameters=payload.parameters,
        enabled=payload.enabled,
        score=payload.score,
        notes=payload.notes,
    )
    session.add(strat)
    await session.commit()
    await session.refresh(strat)
    payload.id = strat.id
    return payload


@router.post("/{strategy_id}/toggle", response_model=StrategyView)
async def toggle_strategy(
    strategy_id: int, session: AsyncSession = Depends(get_session)
) -> StrategyView:
    strat = await session.get(Strategy, strategy_id)
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strat.enabled = not strat.enabled
    await session.commit()
    await session.refresh(strat)
    return StrategyView(
        id=strat.id,
        name=strat.name,
        kind=strat.kind,
        symbol=strat.symbol,
        timeframe=strat.timeframe,
        parameters=strat.parameters or {},
        enabled=strat.enabled,
        score=strat.score,
        notes=strat.notes,
    )
