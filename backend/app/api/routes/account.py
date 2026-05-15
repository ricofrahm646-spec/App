"""Account / equity / margin endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.common import AccountSnapshot
from mt5.connector import get_connector

router = APIRouter()


@router.get("/snapshot", response_model=AccountSnapshot)
async def snapshot() -> AccountSnapshot:
    conn = get_connector()
    return await conn.account_snapshot()


@router.get("/symbols")
async def symbols() -> list[str]:
    conn = get_connector()
    return await conn.symbols()
