from fastapi import APIRouter

from app.dependencies import mt5_connector, risk_engine
from app.models.trading import RiskSnapshot, TradePosition

router = APIRouter()


@router.get("/snapshot", response_model=RiskSnapshot)
def risk_snapshot() -> RiskSnapshot:
    # Placeholder account numbers to be replaced by MT5 account feed.
    return risk_engine.summarize_account(equity=10120.5, margin=532.3, peak_equity=11200.0)


@router.post("/enforce-emergency-close", response_model=list[TradePosition])
def enforce_emergency_close() -> list[TradePosition]:
    closed: list[TradePosition] = []
    for position in mt5_connector.list_open_positions():
        if risk_engine.detect_emergency_close(position):
            result = mt5_connector.close_order(position.ticket)
            if result:
                closed.append(result)
    return closed
