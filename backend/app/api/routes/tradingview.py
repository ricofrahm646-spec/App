"""TradingView webhook receiver + Pine Script generator."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger
from backend.app.schemas.common import TradeRequest
from mt5.connector import get_connector
from risk_management.engine import RiskEngine
from tradingview.pine_generator import PineGenerator

router = APIRouter()


# ── Forex universe (only Forex on the TradingView side) ────────────
_FX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "EURGBP", "EURJPY", "EURCHF", "GBPJPY", "AUDJPY", "CHFJPY", "CADJPY",
    "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
    "AUDCAD", "AUDCHF", "AUDNZD", "NZDCAD", "NZDCHF", "NZDJPY",
}


@router.post("/webhook")
async def webhook(request: Request) -> dict[str, Any]:
    body = await request.json()

    secret = body.get("secret") or request.headers.get("X-TV-Secret", "")
    if secret != settings.tradingview_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    symbol: str = str(body.get("symbol", "")).upper().replace(":", "").replace("FX_", "")
    side: str = str(body.get("side", "")).upper()
    volume: float = float(body.get("volume", 0.01))
    sl = body.get("sl")
    tp = body.get("tp")

    if symbol not in _FX_PAIRS:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} is not a Forex pair")
    if side not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")

    req = TradeRequest(
        symbol=symbol,
        side=side,  # type: ignore[arg-type]
        volume=volume,
        sl=float(sl) if sl is not None else None,
        tp=float(tp) if tp is not None else None,
        comment="tradingview",
    )
    risk = RiskEngine()
    ok, reason = await risk.allow_new_trade(req)
    if not ok:
        logger.warning("TV webhook blocked: {}", reason)
        return {"status": "blocked", "reason": reason}

    conn = get_connector()
    trade = await conn.open(req)
    return {"status": "ok", "trade": trade.model_dump()}


class PineRequest(BaseModel):
    name: str
    strategy_kind: str = "trend_following"
    parameters: dict[str, Any] = {}


@router.post("/pine")
async def generate_pine(req: PineRequest) -> dict[str, str]:
    gen = PineGenerator()
    code = gen.generate(name=req.name, kind=req.strategy_kind, parameters=req.parameters)
    return {"name": req.name, "code": code}
