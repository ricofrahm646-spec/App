"""Backtesting endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backtesting.runner import BacktestConfig, run_backtest
from backtesting.monte_carlo import monte_carlo
from backtesting.walk_forward import walk_forward


router = APIRouter()


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    bars: int = 5000
    parameters: dict[str, Any] = {}


@router.post("/run")
async def run(req: BacktestRequest) -> dict[str, Any]:
    cfg = BacktestConfig(
        strategy=req.strategy,
        symbol=req.symbol,
        timeframe=req.timeframe,
        bars=req.bars,
        parameters=req.parameters,
    )
    return await run_backtest(cfg)


@router.post("/monte-carlo")
async def mc(req: BacktestRequest, n: int = 500) -> dict[str, Any]:
    cfg = BacktestConfig(
        strategy=req.strategy,
        symbol=req.symbol,
        timeframe=req.timeframe,
        bars=req.bars,
        parameters=req.parameters,
    )
    return await monte_carlo(cfg, simulations=n)


@router.post("/walk-forward")
async def wf(req: BacktestRequest, folds: int = 5) -> dict[str, Any]:
    cfg = BacktestConfig(
        strategy=req.strategy,
        symbol=req.symbol,
        timeframe=req.timeframe,
        bars=req.bars,
        parameters=req.parameters,
    )
    return await walk_forward(cfg, folds=folds)
