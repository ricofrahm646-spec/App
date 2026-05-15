from fastapi import APIRouter, HTTPException

from app.dependencies import mt5_connector, risk_engine
from app.models.trading import CloseTradeRequest, TradePosition, TradeRequest
from app.services.risk_engine import RiskEngineError

router = APIRouter()


@router.get("/positions", response_model=list[TradePosition])
def list_positions() -> list[TradePosition]:
    return mt5_connector.list_open_positions()


@router.get("/terminal-context")
def terminal_context() -> dict[str, str | list[str]]:
    return mt5_connector.get_terminal_context()


@router.post("/open", response_model=TradePosition)
def open_trade(payload: TradeRequest) -> TradePosition:
    open_positions = mt5_connector.list_open_positions()
    try:
        risk_engine.validate_new_trade(payload, open_positions)
    except RiskEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return mt5_connector.place_order(payload)


@router.post("/close", response_model=TradePosition)
def close_trade(payload: CloseTradeRequest) -> TradePosition:
    closed = mt5_connector.close_order(payload.ticket)
    if closed is None:
        raise HTTPException(status_code=404, detail="Position not found")
    return closed
