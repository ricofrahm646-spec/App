from fastapi import APIRouter

from app.models.schemas import BacktestRequest, BacktestResult
from app.services.orchestrator import JarvisOrchestrator

router = APIRouter()
orchestrator = JarvisOrchestrator()


@router.post("/run", response_model=BacktestResult)
def run_backtest(request: BacktestRequest) -> BacktestResult:
    return orchestrator.backtesting.run_backtest(request)
