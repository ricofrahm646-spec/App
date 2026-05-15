from fastapi import APIRouter, Depends

from backend.app.dependencies import get_mt5_connector, get_risk_engine
from mt5.connector import MT5Connector
from risk_management.engine import RiskEngine

router = APIRouter(prefix="/risk", tags=["Risk Management"])


@router.get("/status")
async def risk_status(
    connector: MT5Connector = Depends(get_mt5_connector),
    engine: RiskEngine = Depends(get_risk_engine),
) -> dict:
    positions = connector.list_open_positions()
    check = engine.evaluate_existing_positions(positions)
    return {
        "decision": check.decision.value,
        "reason": check.reason,
        "max_open_trades": engine.max_open_trades,
        "forced_close_loss_percent": engine.forced_close_loss_percent,
        "open_positions": [position.__dict__ for position in positions],
    }
