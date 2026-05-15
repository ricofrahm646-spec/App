"""Risk evaluation API."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import get_mt5
from app.services.risk_engine import RiskContext, RiskEngine

router = APIRouter()
_engine = RiskEngine()


class ProposedOrder(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")


@router.post("/evaluate")
async def evaluate(order: ProposedOrder):
    mt5 = get_mt5()
    acc = mt5.account_info()
    positions = mt5.positions()
    if acc is None:
        equity, balance = 0.0, 0.0
    else:
        equity = float(acc.equity or 0)
        balance = float(acc.balance or 0)
    ctx = RiskContext(
        equity=equity,
        balance=balance,
        open_positions=positions,
        proposed_side=order.side,
        proposed_symbol=order.symbol,
    )
    d1, reason1 = _engine.evaluate_new_order(ctx)
    d2, reason2 = _engine.evaluate_emergency(ctx)
    return {
        "new_order": {"decision": d1.value, "reason": reason1},
        "emergency": {"decision": d2.value, "reason": reason2},
    }
