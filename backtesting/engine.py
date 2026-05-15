from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.app.schemas import BacktestRequest, BacktestResult


@dataclass(frozen=True)
class SimulationConfig:
    spread_points: float
    slippage_points: float
    walk_forward_splits: int
    monte_carlo_runs: int


class BacktestEngine:
    """Backtesting facade for tick, vectorized and walk-forward validation."""

    def run(self, request: BacktestRequest, market_data: pd.DataFrame | None = None) -> BacktestResult:
        data = market_data if market_data is not None else self._synthetic_market_data()
        returns = data["close"].pct_change().fillna(0)
        signal = self._ema_signal(data)
        strategy_returns = returns * signal.shift(1).fillna(0)
        adjusted_returns = self._apply_execution_costs(
            strategy_returns,
            spread_points=request.spread_points,
            slippage_points=request.slippage_points,
        )
        trades = self._extract_trade_returns(adjusted_returns)
        total_trades = len(trades)
        wins = [trade for trade in trades if trade > 0]
        losses = [trade for trade in trades if trade < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses)) or 1e-9
        equity_curve = (1 + adjusted_returns).cumprod()
        drawdown = self._max_drawdown(equity_curve)

        notes = [
            "Synthetic sample data used; provide broker tick data for production-grade validation."
            if market_data is None
            else "External market data used.",
            f"Walk-forward splits configured: {request.walk_forward_splits}.",
            f"Monte Carlo runs configured: {request.monte_carlo_runs}.",
            "Results are research metrics, not a profitability promise.",
        ]
        return BacktestResult(
            strategy_name=request.strategy_name,
            symbol=request.symbol,
            timeframe=request.timeframe,
            total_trades=total_trades,
            winrate=round(len(wins) / total_trades * 100, 2) if total_trades else 0.0,
            profit_factor=round(gross_profit / gross_loss, 2),
            max_drawdown_percent=round(drawdown * 100, 2),
            notes=notes,
        )

    def walk_forward(self, data: pd.DataFrame, splits: int) -> list[dict[str, float]]:
        if splits <= 1:
            return []
        chunks = np.array_split(data, splits)
        results = []
        for index, chunk in enumerate(chunks):
            if chunk.empty:
                continue
            returns = chunk["close"].pct_change().fillna(0)
            results.append(
                {
                    "split": float(index + 1),
                    "mean_return": float(returns.mean()),
                    "volatility": float(returns.std()),
                }
            )
        return results

    def monte_carlo(self, trade_returns: list[float], runs: int) -> dict[str, float]:
        if not trade_returns or runs <= 0:
            return {"p05": 0.0, "median": 0.0, "p95": 0.0}
        outcomes = []
        for _ in range(runs):
            sample = np.random.choice(trade_returns, size=len(trade_returns), replace=True)
            outcomes.append(float(np.prod(1 + sample) - 1))
        return {
            "p05": float(np.percentile(outcomes, 5)),
            "median": float(np.percentile(outcomes, 50)),
            "p95": float(np.percentile(outcomes, 95)),
        }

    @staticmethod
    def _synthetic_market_data(rows: int = 1_000) -> pd.DataFrame:
        rng = np.random.default_rng(seed=42)
        returns = rng.normal(loc=0.00005, scale=0.001, size=rows)
        close = 2_000 * np.cumprod(1 + returns)
        return pd.DataFrame({"close": close})

    @staticmethod
    def _ema_signal(data: pd.DataFrame) -> pd.Series:
        fast = data["close"].ewm(span=9).mean()
        slow = data["close"].ewm(span=21).mean()
        return pd.Series(np.where(fast > slow, 1, -1), index=data.index)

    @staticmethod
    def _apply_execution_costs(
        returns: pd.Series,
        *,
        spread_points: float,
        slippage_points: float,
    ) -> pd.Series:
        cost = (spread_points + slippage_points) / 1_000_000
        active = returns.ne(0)
        return returns.where(~active, returns - cost)

    @staticmethod
    def _extract_trade_returns(returns: pd.Series) -> list[float]:
        return [float(value) for value in returns if abs(float(value)) > 0]

    @staticmethod
    def _max_drawdown(equity_curve: pd.Series) -> float:
        peak = equity_curve.cummax()
        drawdown = (peak - equity_curve) / peak
        return float(drawdown.max()) if not drawdown.empty else 0.0
