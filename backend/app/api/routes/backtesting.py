"""
Backtesting Router - run backtests, walk-forward, Monte Carlo, compare results.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.backtest import BacktestResult, BacktestStatus
from app.services.backtest_service import BacktestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtesting", tags=["backtesting"])


# ─────────────────────────────────────── Request / Response models ────────────

class BacktestRequest(BaseModel):
    strategy_id: Optional[int] = Field(None, description="ID of existing strategy (optional)")
    strategy_name: Optional[str] = Field(None, description="Override strategy name")
    symbol: str = Field(..., description="Trading symbol, e.g. EURUSD")
    timeframe: str = Field(..., description="Timeframe, e.g. H1, M15, D1")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    initial_capital: float = Field(10000.0, gt=0, description="Starting capital in account currency")
    commission: float = Field(0.0001, ge=0, description="Commission per lot (as fraction)")
    slippage: float = Field(0.0001, ge=0, description="Slippage as fraction")


class WalkForwardRequest(BacktestRequest):
    segments: Optional[int] = Field(None, ge=2, le=24, description="Number of WF segments (auto if None)")


class MonteCarloRequest(BacktestRequest):
    simulations: int = Field(1000, ge=100, le=10000, description="Number of Monte Carlo iterations")


class CompareRequest(BaseModel):
    result_ids: List[int] = Field(..., min_length=2, description="List of backtest result IDs to compare")


def _backtest_to_dict(r: BacktestResult) -> Dict[str, Any]:
    return {
        "id": r.id,
        "strategy_id": r.strategy_id,
        "strategy_name": r.strategy_name,
        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        "symbol": r.symbol,
        "timeframe": r.timeframe,
        "start_date": r.start_date,
        "end_date": r.end_date,
        "backtest_type": r.backtest_type,
        "initial_capital": r.initial_capital,
        "final_balance": r.final_balance,
        "total_return": r.total_return,
        "total_return_pct": r.total_return_pct,
        "total_trades": r.total_trades,
        "winning_trades": r.winning_trades,
        "losing_trades": r.losing_trades,
        "win_rate": r.win_rate,
        "profit_factor": r.profit_factor,
        "max_drawdown": r.max_drawdown,
        "max_drawdown_pct": r.max_drawdown_pct,
        "sharpe_ratio": r.sharpe_ratio,
        "sortino_ratio": r.sortino_ratio,
        "calmar_ratio": r.calmar_ratio,
        "avg_win": r.avg_win,
        "avg_loss": r.avg_loss,
        "avg_trade_duration": r.avg_trade_duration,
        "max_consecutive_wins": r.max_consecutive_wins,
        "max_consecutive_losses": r.max_consecutive_losses,
        "error_message": r.error_message,
        "duration_seconds": r.duration_seconds,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


# ─────────────────────────────────────────────────────── Endpoints ────────────

@router.post("/run", summary="Run a full backtest", status_code=status.HTTP_201_CREATED)
async def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Execute a full historical backtest for the given strategy and parameters.
    Returns complete performance metrics and equity curve.
    """
    try:
        result = await BacktestService.run_backtest(db, req.model_dump())
        data = _backtest_to_dict(result)
        data["equity_curve"] = result.equity_curve
        data["monthly_returns"] = result.monthly_returns
        return data
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Backtest run failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/walkforward", summary="Walk-forward analysis")
async def run_walkforward(req: WalkForwardRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Perform a walk-forward analysis by splitting the date range into sequential
    in-sample and out-of-sample segments.  Returns per-segment results and summary.
    """
    try:
        params = req.model_dump()
        return await BacktestService.run_walkforward(db, params)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Walk-forward failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/montecarlo", summary="Monte Carlo simulation")
async def run_montecarlo(req: MonteCarloRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation by randomizing trade order N times.
    Provides probability of profit, distribution of returns, and worst-case drawdown.
    """
    try:
        params = req.model_dump()
        return await BacktestService.run_montecarlo(db, params)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Monte Carlo failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/results", summary="List backtest results")
def list_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return a paginated list of all stored backtest results."""
    results = BacktestService.list_results(db, skip=skip, limit=limit)
    return [_backtest_to_dict(r) for r in results]


@router.get("/results/{result_id}", summary="Get specific backtest result")
def get_result(result_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Return full details for a single backtest result including
    equity curve, monthly returns, and individual trade list.
    """
    result = BacktestService.get_result(db, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Result #{result_id} not found")
    data = _backtest_to_dict(result)
    data["equity_curve"] = result.equity_curve
    data["monthly_returns"] = result.monthly_returns
    data["trades"] = result.trades_data
    data["detailed_results"] = result.detailed_results
    return data


@router.delete("/results/{result_id}", summary="Delete backtest result")
def delete_result(result_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Permanently remove a backtest result and its associated data."""
    deleted = BacktestService.delete_result(db, result_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Result #{result_id} not found")
    return {"deleted": True, "result_id": result_id}


@router.get("/compare", summary="Compare multiple strategy results")
def compare_strategies(
    ids: str = Query(..., description="Comma-separated list of result IDs, e.g. 1,2,3"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Side-by-side comparison of multiple backtest results ranked by composite score.
    Pass result IDs as a comma-separated query parameter: ?ids=1,2,3
    """
    try:
        result_ids = [int(i.strip()) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ids must be comma-separated integers",
        )
    if len(result_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least 2 result IDs to compare",
        )
    return BacktestService.compare_strategies(db, result_ids)
