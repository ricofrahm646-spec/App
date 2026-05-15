from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    APIResponse,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    BacktestStatus,
    BacktestTradeResult,
    MonteCarloRequest,
    MonteCarloResult,
    OrderSide,
    WalkForwardRequest,
    WalkForwardResult,
)

logger = structlog.get_logger("jarvis.backtesting")
router = APIRouter(prefix="/backtesting", tags=["Backtesting"])

_backtests: dict[str, BacktestResponse] = {}
_walk_forward_results: dict[str, WalkForwardResult] = {}
_monte_carlo_results: dict[str, MonteCarloResult] = {}


def _simulate_backtest(request: BacktestRequest) -> BacktestResponse:
    """Generate a deterministic-seeded simulated backtest result."""
    bt_id = uuid.uuid4().hex[:12]
    seed = hash(f"{request.strategy_id}{request.symbol}{request.start_date}")
    rng = random.Random(seed)

    num_trades = rng.randint(40, 200)
    trades: list[BacktestTradeResult] = []
    capital = request.initial_capital
    equity_curve = [capital]
    wins = 0

    total_seconds = int(
        (request.end_date - request.start_date).total_seconds()
    )
    interval = max(total_seconds // (num_trades + 1), 60)

    for i in range(num_trades):
        entry_offset = interval * (i + 1)
        entry_time = request.start_date.replace(tzinfo=timezone.utc) if request.start_date.tzinfo is None else request.start_date
        entry_time = entry_time.__class__(
            *entry_time.timetuple()[:6], tzinfo=timezone.utc
        )
        from datetime import timedelta

        entry_dt = entry_time + timedelta(seconds=entry_offset)
        duration = rng.randint(5, 480)
        exit_dt = entry_dt + timedelta(minutes=duration)

        side = OrderSide.BUY if rng.random() > 0.5 else OrderSide.SELL
        entry_price = round(rng.uniform(1.05, 1.15), 5)
        pnl_pips = rng.gauss(2, 30)
        pip_value = 0.0001
        profit = round(pnl_pips * pip_value * request.volume if hasattr(request, "volume") else pnl_pips * pip_value * 100000 * 0.1, 2)
        profit = round(pnl_pips * 0.1 * request.initial_capital / 10000, 2)
        commission = round(request.commission * request.initial_capital * 0.01, 2)
        net = profit - commission

        exit_price = round(
            entry_price + (pnl_pips * pip_value * (1 if side == OrderSide.BUY else -1)),
            5,
        )

        if net > 0:
            wins += 1

        capital += net
        equity_curve.append(round(capital, 2))

        trades.append(
            BacktestTradeResult(
                entry_time=entry_dt,
                exit_time=exit_dt,
                symbol=request.symbol,
                side=side,
                volume=0.1,
                entry_price=entry_price,
                exit_price=exit_price,
                profit=round(net, 2),
                commission=commission,
                duration_minutes=duration,
            )
        )

    total_profit = round(capital - request.initial_capital, 2)
    losses = num_trades - wins
    avg_win = (
        round(sum(t.profit for t in trades if t.profit > 0) / max(wins, 1), 2)
    )
    avg_loss = (
        round(sum(t.profit for t in trades if t.profit <= 0) / max(losses, 1), 2)
    )
    gross_profit = sum(t.profit for t in trades if t.profit > 0)
    gross_loss = abs(sum(t.profit for t in trades if t.profit <= 0))

    peak = request.initial_capital
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    metrics = BacktestMetrics(
        total_trades=num_trades,
        winning_trades=wins,
        losing_trades=losses,
        win_rate=round(wins / num_trades * 100, 2) if num_trades else 0,
        profit_factor=round(gross_profit / gross_loss, 2) if gross_loss else 0,
        total_profit=total_profit,
        max_drawdown=round(max_dd, 2),
        max_drawdown_pct=round(max_dd / request.initial_capital * 100, 2),
        sharpe_ratio=round(rng.uniform(0.5, 2.5), 2),
        sortino_ratio=round(rng.uniform(0.8, 3.0), 2),
        calmar_ratio=round(total_profit / max(max_dd, 1), 2),
        avg_trade_profit=round(total_profit / num_trades, 2) if num_trades else 0,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=round(max((t.profit for t in trades), default=0), 2),
        largest_loss=round(min((t.profit for t in trades), default=0), 2),
        avg_holding_time_minutes=round(
            sum(t.duration_minutes for t in trades) / max(num_trades, 1), 1
        ),
        max_consecutive_wins=rng.randint(3, 12),
        max_consecutive_losses=rng.randint(2, 8),
        expectancy=round(
            (wins / num_trades * avg_win + losses / num_trades * avg_loss)
            if num_trades
            else 0,
            2,
        ),
        recovery_factor=round(total_profit / max(max_dd, 1), 2),
        final_capital=round(capital, 2),
    )

    return BacktestResponse(
        id=bt_id,
        strategy_id=request.strategy_id,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        status=BacktestStatus.COMPLETED,
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        created_at=datetime.now(timezone.utc),
        duration_seconds=round(rng.uniform(0.5, 5.0), 2),
    )


# ── Run backtest ─────────────────────────────────────────────────────────

@router.post(
    "/run",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run a backtest",
)
async def run_backtest(request: BacktestRequest) -> APIResponse:
    logger.info(
        "backtest_started",
        strategy_id=request.strategy_id,
        symbol=request.symbol,
        timeframe=request.timeframe.value,
    )

    result = _simulate_backtest(request)
    _backtests[result.id] = result

    logger.info(
        "backtest_completed",
        id=result.id,
        total_trades=result.metrics.total_trades if result.metrics else 0,
        total_profit=result.metrics.total_profit if result.metrics else 0,
    )
    return APIResponse(
        success=True,
        message="Backtest completed.",
        data=result.model_dump(mode="json"),
    )


# ── Get backtest result ──────────────────────────────────────────────────

@router.get(
    "/{backtest_id}",
    response_model=APIResponse,
    summary="Get backtest result by ID",
)
async def get_backtest(backtest_id: str) -> APIResponse:
    result = _backtests.get(backtest_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {backtest_id} not found.",
        )
    return APIResponse(success=True, data=result.model_dump(mode="json"))


# ── List backtests ───────────────────────────────────────────────────────

@router.get(
    "",
    response_model=APIResponse,
    summary="List all backtests",
)
async def list_backtests() -> APIResponse:
    items = sorted(
        _backtests.values(), key=lambda b: b.created_at, reverse=True
    )
    return APIResponse(
        success=True,
        data=[b.model_dump(mode="json") for b in items],
    )


# ── Walk-forward analysis ───────────────────────────────────────────────

@router.post(
    "/walk-forward",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run walk-forward analysis",
)
async def run_walk_forward(request: WalkForwardRequest) -> APIResponse:
    logger.info("walk_forward_started", strategy_id=request.strategy_id)

    total_seconds = int(
        (request.end_date - request.start_date).total_seconds()
    )
    fold_seconds = total_seconds // request.num_folds
    folds: list[BacktestResponse] = []

    from datetime import timedelta

    for i in range(request.num_folds):
        fold_start = request.start_date + timedelta(seconds=fold_seconds * i)
        fold_end = request.start_date + timedelta(seconds=fold_seconds * (i + 1))
        bt_req = BacktestRequest(
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=fold_start,
            end_date=fold_end,
            initial_capital=request.initial_capital,
            parameters=request.parameters,
        )
        fold_result = _simulate_backtest(bt_req)
        folds.append(fold_result)
        _backtests[fold_result.id] = fold_result

    combined = BacktestMetrics(
        total_trades=sum(f.metrics.total_trades for f in folds if f.metrics),
        winning_trades=sum(f.metrics.winning_trades for f in folds if f.metrics),
        losing_trades=sum(f.metrics.losing_trades for f in folds if f.metrics),
        total_profit=round(sum(f.metrics.total_profit for f in folds if f.metrics), 2),
        final_capital=round(
            request.initial_capital
            + sum(f.metrics.total_profit for f in folds if f.metrics),
            2,
        ),
    )
    total = combined.total_trades
    if total:
        combined.win_rate = round(combined.winning_trades / total * 100, 2)
        combined.avg_trade_profit = round(combined.total_profit / total, 2)

    profitable_folds = sum(
        1 for f in folds if f.metrics and f.metrics.total_profit > 0
    )
    robustness = round(profitable_folds / max(len(folds), 1) * 100, 2)

    wf_id = uuid.uuid4().hex[:12]
    wf_result = WalkForwardResult(
        id=wf_id,
        folds=folds,
        combined_metrics=combined,
        robustness_score=robustness,
    )
    _walk_forward_results[wf_id] = wf_result

    logger.info(
        "walk_forward_completed", id=wf_id, robustness=robustness
    )
    return APIResponse(
        success=True,
        message="Walk-forward analysis completed.",
        data=wf_result.model_dump(mode="json"),
    )


# ── Monte Carlo simulation ──────────────────────────────────────────────

@router.post(
    "/monte-carlo",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Monte Carlo simulation",
)
async def run_monte_carlo(request: MonteCarloRequest) -> APIResponse:
    bt = _backtests.get(request.backtest_id)
    if not bt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {request.backtest_id} not found.",
        )
    if not bt.trades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest has no trades to simulate.",
        )

    logger.info(
        "monte_carlo_started",
        backtest_id=request.backtest_id,
        simulations=request.num_simulations,
    )

    trade_pnls = [t.profit for t in bt.trades]
    rng = random.Random(42)
    final_equities: list[float] = []
    initial = bt.metrics.final_capital - bt.metrics.total_profit if bt.metrics else 10000

    for _ in range(request.num_simulations):
        shuffled = trade_pnls[:]
        rng.shuffle(shuffled)
        equity = initial
        for pnl in shuffled:
            equity += pnl
        final_equities.append(round(equity, 2))

    final_equities.sort()
    n = len(final_equities)

    percentile_keys = [5, 10, 25, 50, 75, 90, 95]
    percentiles = {
        str(p): final_equities[int(n * p / 100)] for p in percentile_keys
    }

    ruin_threshold = initial * 0.5
    ruin_count = sum(1 for e in final_equities if e <= ruin_threshold)

    ci_idx = int(n * (1 - request.confidence_level))
    var_95 = initial - final_equities[int(n * 0.05)]
    cvar_95 = initial - round(
        sum(final_equities[: int(n * 0.05) + 1]) / max(int(n * 0.05) + 1, 1), 2
    )

    mc_id = uuid.uuid4().hex[:12]
    mc_result = MonteCarloResult(
        id=mc_id,
        backtest_id=request.backtest_id,
        num_simulations=request.num_simulations,
        confidence_level=request.confidence_level,
        median_final_equity=final_equities[n // 2],
        worst_case_equity=final_equities[0],
        best_case_equity=final_equities[-1],
        probability_of_ruin=round(ruin_count / n * 100, 2),
        var_95=round(var_95, 2),
        cvar_95=round(cvar_95, 2),
        equity_percentiles=percentiles,
    )
    _monte_carlo_results[mc_id] = mc_result

    logger.info("monte_carlo_completed", id=mc_id)
    return APIResponse(
        success=True,
        message="Monte Carlo simulation completed.",
        data=mc_result.model_dump(mode="json"),
    )
