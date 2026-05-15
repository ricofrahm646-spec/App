"""System control endpoints: kill switch, status, version."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.config import settings
from mt5.connector import get_connector
from risk_management.engine import RiskEngine

router = APIRouter()


@router.get("/status")
async def status() -> dict[str, object]:
    conn = get_connector()
    return {
        "app": settings.app_name,
        "env": settings.app_env,
        "mt5_mode": "mock" if settings.mt5_mock else "live",
        "connected": await conn.is_connected(),
        "kill_switch": RiskEngine.kill_switch_active(),
    }


@router.post("/kill-switch")
async def kill_switch() -> dict[str, str]:
    await RiskEngine.activate_kill_switch()
    return {"status": "engaged"}


@router.post("/resume")
async def resume() -> dict[str, str]:
    RiskEngine.release_kill_switch()
    return {"status": "released"}
