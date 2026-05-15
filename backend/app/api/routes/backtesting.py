from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.dependencies import backtesting_service
from app.services.backtesting_service import BacktestResult

router = APIRouter()


class BacktestRequest(BaseModel):
    strategy_id: str = Field(..., min_length=2)
    symbol: str = Field(..., min_length=3)
    timeframe: str = Field(..., min_length=1)


@router.post("/run", response_model=BacktestResult)
def run_backtest(payload: BacktestRequest) -> BacktestResult:
    return backtesting_service.run_backtest(
        strategy_id=payload.strategy_id, symbol=payload.symbol, timeframe=payload.timeframe
    )
