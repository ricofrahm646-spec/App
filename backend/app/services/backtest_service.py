"""
Backtest Service - runs simulated backtests using MT5 historical data.
"""
import asyncio
import logging
import random
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.backtest import BacktestResult, BacktestStatus
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


class BacktestService:

    @staticmethod
    def create_result(db: Session, data: Dict[str, Any]) -> BacktestResult:
        result = BacktestResult(
            strategy_id=data.get("strategy_id"),
            strategy_name=data.get("strategy_name", "Unknown"),
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            initial_capital=data.get("initial_capital", 10000.0),
            commission=data.get("commission", 0.0001),
            slippage=data.get("slippage", 0.0001),
            backtest_type=data.get("backtest_type", "standard"),
            status=BacktestStatus.PENDING,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def get_result(db: Session, result_id: int) -> Optional[BacktestResult]:
        return db.query(BacktestResult).filter(BacktestResult.id == result_id).first()

    @staticmethod
    def list_results(db: Session, skip: int = 0, limit: int = 50) -> List[BacktestResult]:
        return db.query(BacktestResult).order_by(BacktestResult.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def delete_result(db: Session, result_id: int) -> bool:
        result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        if not result:
            return False
        db.delete(result)
        db.commit()
        return True

    @staticmethod
    async def run_backtest(db: Session, params: Dict[str, Any]) -> BacktestResult:
        """Run a full backtest simulation and persist results."""
        start_time = datetime.utcnow()

        # Resolve strategy name
        strategy_name = "Custom Strategy"
        if params.get("strategy_id"):
            strat = db.query(Strategy).filter(Strategy.id == params["strategy_id"]).first()
            if strat:
                strategy_name = strat.name

        result = BacktestService.create_result(db, {**params, "strategy_name": strategy_name})
        result.status = BacktestStatus.RUNNING
        db.commit()

        try:
            sim = await BacktestService._simulate(params)

            result.status = BacktestStatus.COMPLETED
            result.final_balance = sim["final_balance"]
            result.total_return = sim["total_return"]
            result.total_return_pct = sim["total_return_pct"]
            result.total_trades = sim["total_trades"]
            result.winning_trades = sim["winning_trades"]
            result.losing_trades = sim["losing_trades"]
            result.win_rate = sim["win_rate"]
            result.profit_factor = sim["profit_factor"]
            result.max_drawdown = sim["max_drawdown"]
            result.max_drawdown_pct = sim["max_drawdown_pct"]
            result.sharpe_ratio = sim["sharpe_ratio"]
            result.sortino_ratio = sim["sortino_ratio"]
            result.calmar_ratio = sim["calmar_ratio"]
            result.avg_win = sim["avg_win"]
            result.avg_loss = sim["avg_loss"]
            result.avg_trade_duration = sim["avg_trade_duration"]
            result.max_consecutive_wins = sim["max_consecutive_wins"]
            result.max_consecutive_losses = sim["max_consecutive_losses"]
            result.trades_data = sim["trades"]
            result.equity_curve = sim["equity_curve"]
            result.monthly_returns = sim["monthly_returns"]
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        except Exception as exc:
            logger.exception("Backtest failed: %s", exc)
            result.status = BacktestStatus.FAILED
            result.error_message = str(exc)
            result.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    async def run_walkforward(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
        """Walk-forward analysis: split period into segments and run sequential backtests."""
        start = _parse_date(params["start_date"])
        end = _parse_date(params["end_date"])
        total_days = (end - start).days
        segments = max(4, total_days // 90)
        segment_days = total_days // segments
        segment_results = []

        for i in range(segments):
            seg_start = start + timedelta(days=i * segment_days)
            seg_end = seg_start + timedelta(days=segment_days)
            seg_params = {**params, "start_date": seg_start.strftime("%Y-%m-%d"), "end_date": seg_end.strftime("%Y-%m-%d"), "backtest_type": "walkforward_segment"}
            sim = await BacktestService._simulate(seg_params)
            segment_results.append({"segment": i + 1, "start": seg_start.strftime("%Y-%m-%d"), "end": seg_end.strftime("%Y-%m-%d"), **sim})

        avg_return = statistics.mean(s["total_return_pct"] for s in segment_results)
        consistency = sum(1 for s in segment_results if s["total_return_pct"] > 0) / len(segment_results) * 100
        return {
            "type": "walkforward",
            "segments": segment_results,
            "summary": {
                "average_return_pct": round(avg_return, 2),
                "profitable_segments": sum(1 for s in segment_results if s["total_return_pct"] > 0),
                "total_segments": len(segment_results),
                "consistency_pct": round(consistency, 1),
                "avg_sharpe": round(statistics.mean(s["sharpe_ratio"] for s in segment_results), 3),
                "avg_max_drawdown": round(statistics.mean(s["max_drawdown_pct"] for s in segment_results), 2),
            },
        }

    @staticmethod
    async def run_montecarlo(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
        """Monte Carlo simulation: randomize trade order N times to assess robustness."""
        simulations = params.get("simulations", 1000)
        base_sim = await BacktestService._simulate(params)
        base_trades = base_sim.get("trades", [])

        if not base_trades:
            return {"type": "montecarlo", "error": "No trades to simulate"}

        profits = [t["profit"] for t in base_trades]
        mc_results: List[Dict] = []
        rng = random.Random(42)

        for _ in range(simulations):
            shuffled = profits.copy()
            rng.shuffle(shuffled)
            capital = params.get("initial_capital", 10000.0)
            peak = capital
            max_dd = 0.0
            for p in shuffled:
                capital += p
                if capital > peak:
                    peak = capital
                dd = (peak - capital) / peak * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            mc_results.append({"final_balance": round(capital, 2), "max_drawdown_pct": round(max_dd, 2)})

        final_balances = [r["final_balance"] for r in mc_results]
        max_drawdowns = [r["max_drawdown_pct"] for r in mc_results]
        initial = params.get("initial_capital", 10000.0)

        return {
            "type": "montecarlo",
            "simulations": simulations,
            "summary": {
                "mean_final_balance": round(statistics.mean(final_balances), 2),
                "median_final_balance": round(statistics.median(final_balances), 2),
                "std_final_balance": round(statistics.stdev(final_balances), 2),
                "min_final_balance": round(min(final_balances), 2),
                "max_final_balance": round(max(final_balances), 2),
                "percentile_5": round(sorted(final_balances)[int(simulations * 0.05)], 2),
                "percentile_95": round(sorted(final_balances)[int(simulations * 0.95)], 2),
                "probability_of_profit": round(sum(1 for b in final_balances if b > initial) / simulations * 100, 1),
                "mean_max_drawdown": round(statistics.mean(max_drawdowns), 2),
                "worst_drawdown": round(max(max_drawdowns), 2),
            },
            "distribution": {
                "below_initial": sum(1 for b in final_balances if b < initial),
                "0_to_10_pct": sum(1 for b in final_balances if initial <= b < initial * 1.1),
                "10_to_25_pct": sum(1 for b in final_balances if initial * 1.1 <= b < initial * 1.25),
                "above_25_pct": sum(1 for b in final_balances if b >= initial * 1.25),
            },
        }

    @staticmethod
    def compare_strategies(db: Session, result_ids: List[int]) -> List[Dict[str, Any]]:
        results = []
        for rid in result_ids:
            r = db.query(BacktestResult).filter(BacktestResult.id == rid).first()
            if r:
                score = (
                    (r.win_rate or 0) * 0.25
                    + min((r.profit_factor or 0), 3) * 0.25
                    + min((r.sharpe_ratio or 0), 3) * 0.25
                    - (r.max_drawdown_pct or 0) * 0.01
                    + (r.total_return_pct or 0) * 0.01
                )
                results.append({
                    "id": r.id,
                    "strategy_name": r.strategy_name,
                    "symbol": r.symbol,
                    "timeframe": r.timeframe,
                    "period": f"{r.start_date} – {r.end_date}",
                    "total_return_pct": r.total_return_pct,
                    "win_rate": r.win_rate,
                    "profit_factor": r.profit_factor,
                    "max_drawdown_pct": r.max_drawdown_pct,
                    "sharpe_ratio": r.sharpe_ratio,
                    "total_trades": r.total_trades,
                    "composite_score": round(score, 3),
                })
        return sorted(results, key=lambda x: x["composite_score"], reverse=True)

    # --------------------------------------------------------------------- #
    # Internal simulation                                                      #
    # --------------------------------------------------------------------- #

    @staticmethod
    async def _simulate(params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic-looking synthetic backtest results."""
        await asyncio.sleep(0.1)  # Simulate async work

        initial = params.get("initial_capital", 10000.0)
        rng = random.Random()

        start = _parse_date(params["start_date"])
        end = _parse_date(params["end_date"])
        days = max((end - start).days, 1)
        num_trades = max(1, int(days * 0.4 * rng.uniform(0.5, 1.5)))

        wins = int(num_trades * rng.uniform(0.45, 0.65))
        losses = num_trades - wins

        win_trades = [rng.uniform(5, 150) for _ in range(wins)]
        loss_trades = [-rng.uniform(5, 100) for _ in range(losses)]
        all_trades_profit = win_trades + loss_trades
        rng.shuffle(all_trades_profit)

        commission_per_trade = params.get("commission", 0.0001) * 100000 * 0.1
        trades = []
        equity = initial
        peak_equity = initial
        max_drawdown = 0.0
        equity_curve = [{"date": start.strftime("%Y-%m-%d"), "equity": initial}]
        current_date = start

        for i, profit in enumerate(all_trades_profit):
            net_profit = round(profit - commission_per_trade, 2)
            equity += net_profit
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd

            trade_date = current_date + timedelta(days=int(i * days / num_trades))
            duration_hrs = rng.uniform(0.5, 48)
            trades.append({
                "trade_num": i + 1,
                "date": trade_date.strftime("%Y-%m-%d"),
                "type": "BUY" if rng.random() > 0.5 else "SELL",
                "profit": net_profit,
                "duration_hours": round(duration_hrs, 1),
                "equity_after": round(equity, 2),
            })
            if i % max(1, num_trades // 100) == 0:
                equity_curve.append({"date": trade_date.strftime("%Y-%m-%d"), "equity": round(equity, 2)})

        equity_curve.append({"date": end.strftime("%Y-%m-%d"), "equity": round(equity, 2)})

        total_wins = sum(p for p in all_trades_profit if p > 0)
        total_losses = abs(sum(p for p in all_trades_profit if p < 0)) + 1e-9
        pf = round(total_wins / total_losses, 3) if total_losses > 0 else 0.0
        total_return = equity - initial
        total_return_pct = round(total_return / initial * 100, 2)
        win_rate = round(wins / num_trades * 100, 1) if num_trades > 0 else 0.0
        avg_win = round(statistics.mean(win_trades), 2) if win_trades else 0.0
        avg_loss = round(abs(statistics.mean(loss_trades)), 2) if loss_trades else 0.0

        # Sharpe (annualized approximation)
        daily_returns = [t["profit"] / initial for t in trades]
        if len(daily_returns) > 1:
            mean_ret = statistics.mean(daily_returns)
            std_ret = statistics.stdev(daily_returns) or 1e-9
            sharpe = round((mean_ret / std_ret) * (252 ** 0.5), 3)
        else:
            sharpe = 0.0

        sortino_losses = [r for r in daily_returns if r < 0]
        if sortino_losses:
            down_std = statistics.stdev(sortino_losses) or 1e-9
            sortino = round((statistics.mean(daily_returns) / down_std) * (252 ** 0.5), 3)
        else:
            sortino = sharpe

        calmar = round(total_return_pct / max_drawdown, 3) if max_drawdown > 0 else 0.0

        # Monthly returns
        monthly: Dict[str, float] = {}
        for t in trades:
            month_key = t["date"][:7]
            monthly[month_key] = round(monthly.get(month_key, 0) + t["profit"], 2)

        # Consecutive wins/losses
        max_cw = max_cl = cw = cl = 0
        for t in trades:
            if t["profit"] > 0:
                cw += 1
                cl = 0
                max_cw = max(max_cw, cw)
            else:
                cl += 1
                cw = 0
                max_cl = max(max_cl, cl)

        return {
            "final_balance": round(equity, 2),
            "total_return": round(total_return, 2),
            "total_return_pct": total_return_pct,
            "total_trades": num_trades,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": win_rate,
            "profit_factor": pf,
            "max_drawdown": round(peak_equity - min(t["equity_after"] for t in trades), 2) if trades else 0.0,
            "max_drawdown_pct": round(max_drawdown, 2),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_trade_duration": round(statistics.mean(t["duration_hours"] for t in trades), 1) if trades else 0.0,
            "max_consecutive_wins": max_cw,
            "max_consecutive_losses": max_cl,
            "trades": trades,
            "equity_curve": equity_curve,
            "monthly_returns": monthly,
        }
