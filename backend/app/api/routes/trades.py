"""Trade execution and management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.schemas.common import TradeRequest, TradeView
from mt5.connector import get_connector
from risk_management.engine import RiskEngine

router = APIRouter()


@router.get("/open", response_model=list[TradeView])
async def list_open() -> list[TradeView]:
    conn = get_connector()
    return await conn.open_positions()


@router.get("/history", response_model=list[TradeView])
async def history(limit: int = 50) -> list[TradeView]:
    conn = get_connector()
    return await conn.history(limit=limit)


@router.post("/open", response_model=TradeView)
async def open_trade(req: TradeRequest) -> TradeView:
    risk = RiskEngine()
    ok, reason = await risk.allow_new_trade(req)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Risk engine blocked trade: {reason}")
    conn = get_connector()
    return await conn.open(req)


@router.post("/close/{ticket}", response_model=TradeView)
async def close_trade(ticket: int) -> TradeView:
    conn = get_connector()
    closed = await conn.close(ticket)
    if not closed:
        raise HTTPException(status_code=404, detail="Trade not found")
    return closed


@router.post("/close-all")
async def close_all() -> dict[str, int]:
    conn = get_connector()
    n = await conn.close_all()
    return {"closed": n}
