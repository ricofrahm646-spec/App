"""Backtesting API."""

from fastapi import APIRouter

from app.services.backtest_engine import BacktestEngine, BacktestRequest

router = APIRouter()
_engine = BacktestEngine()


@router.post("/run")
async def run_backtest(req: BacktestRequest):
    return _engine.run_vectorbt_stub(req)
