from fastapi import APIRouter, Depends

from backend.app.dependencies import get_backtest_engine
from backend.app.schemas import BacktestRequest, BacktestResult
from backtesting.engine import BacktestEngine

router = APIRouter(prefix="/backtesting", tags=["Backtesting"])


@router.post("/run", response_model=BacktestResult)
async def run_backtest(
    request: BacktestRequest,
    engine: BacktestEngine = Depends(get_backtest_engine),
) -> BacktestResult:
    return engine.run(request)
