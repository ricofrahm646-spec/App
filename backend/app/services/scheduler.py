"""APScheduler wrapper for periodic background tasks (metrics broadcast, risk checks)."""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.logging_setup import logger
from backend.app.services.ws_manager import manager
from mt5.connector import get_connector
from risk_management.engine import RiskEngine


scheduler = AsyncIOScheduler()


async def broadcast_account_snapshot() -> None:
    conn = get_connector()
    snapshot = await conn.account_snapshot()
    trades = await conn.open_positions()
    await manager.broadcast(
        {
            "topic": "account",
            "payload": snapshot.model_dump(),
        }
    )
    await manager.broadcast(
        {
            "topic": "trades.open",
            "payload": [t.model_dump() for t in trades],
        }
    )


async def enforce_risk_rules() -> None:
    engine = RiskEngine()
    await engine.enforce()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(broadcast_account_snapshot, "interval", seconds=2, id="account-snapshot")
    scheduler.add_job(enforce_risk_rules, "interval", seconds=3, id="risk-enforce")
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
