from fastapi import APIRouter, HTTPException

from app.models.schemas import TradeRequest, TradeState
from app.services.orchestrator import JarvisOrchestrator
from app.services.risk_engine import AccountSnapshot

router = APIRouter()
orchestrator = JarvisOrchestrator()


@router.get("/state", response_model=TradeState)
def get_trade_state() -> TradeState:
    return orchestrator.mt5.get_trade_state()


@router.post("/open", response_model=TradeState)
def open_trade(request: TradeRequest) -> TradeState:
    current_state = orchestrator.mt5.get_trade_state()
    decision = orchestrator.risk_engine.evaluate_open_trade(
        trade_request=request,
        current_state=current_state,
        account=AccountSnapshot(balance=10000, equity=9800, margin_level=250),
    )
    if not decision.approved:
        raise HTTPException(status_code=400, detail=decision.reason)

    return orchestrator.mt5.open_trade(request=request, entry_price=1.2345)


@router.post("/close", response_model=TradeState)
def close_trade() -> TradeState:
    return orchestrator.mt5.close_trade()
