"""Core backtesting engine for JARVIS AI Trading OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from backtesting.analysis.monte_carlo import MonteCarlo, MonteCarloResult
from backtesting.analysis.walk_forward import (
    EvaluateFunc,
    OptimizeFunc,
    WalkForwardAnalyzer,
    WalkForwardResult,
)
from strategies.base_strategy import BaseStrategy, Direction, Signal


# ======================================================================
# Data containers
# ======================================================================


class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Trade:
    """Record of a single round-trip trade."""

    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: TradeDirection
    entry_price: float
    exit_price: float
    sl: Optional[float]
    tp: Optional[float]
    pnl: float
    pnl_pct: float
    bars_held: int
    exit_reason: str = "signal"  # signal | sl | tp


@dataclass(frozen=True)
class BacktestResult:
    """Complete output of a backtest run."""

    # Trade list & curves
    trades: List[Trade]
    equity_curve: pd.Series
    drawdown_curve: pd.Series

    # Core metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float

    # Risk-adjusted
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Extra
    avg_trade_pnl: float
    avg_winner: float
    avg_loser: float
    largest_winner: float
    largest_loser: float
    avg_bars_held: float
    expectancy: float

    parameters: Dict[str, Any] = field(default_factory=dict)


# ======================================================================
# Configuration
# ======================================================================


class BarMode(Enum):
    BAR = "BAR"
    TICK = "TICK"


@dataclass
class BacktestConfig:
    """User-tuneable knobs for a backtest run."""

    initial_equity: float = 10_000.0
    lot_size: float = 1.0
    slippage_pips: float = 0.5
    spread_pips: float = 1.0
    pip_value: float = 0.0001  # for most forex pairs
    commission_per_lot: float = 0.0
    mode: BarMode = BarMode.BAR
    risk_free_rate: float = 0.0
    annualisation_factor: int = 252


# ======================================================================
# Engine
# ======================================================================


class BacktestEngine:
    """Event-driven backtest engine.

    Parameters
    ----------
    strategy : BaseStrategy
        The strategy to test.
    config : BacktestConfig | None
        Override defaults for slippage, spread, equity, etc.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        config: Optional[BacktestConfig] = None,
    ) -> None:
        self.strategy = strategy
        self.cfg = config or BacktestConfig()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, data: pd.DataFrame) -> BacktestResult:
        """Execute the backtest on *data*.

        ``data`` must have columns ``open, high, low, close`` and a
        ``DatetimeIndex`` (or a ``datetime`` column that will be promoted).
        """
        data = self._prepare(data)
        trades = self._simulate(data)
        equity = self._build_equity_curve(trades, data)
        dd, dd_pct = self._compute_drawdown(equity)
        metrics = self._compute_metrics(trades, equity, dd_pct)
        return BacktestResult(
            trades=trades,
            equity_curve=equity,
            drawdown_curve=dd_pct,
            parameters=self.strategy.get_parameters(),
            **metrics,
        )

    # ------------------------------------------------------------------
    # Walk-forward convenience
    # ------------------------------------------------------------------

    def walk_forward(
        self,
        data: pd.DataFrame,
        optimize_fn: OptimizeFunc,
        evaluate_fn: Optional[EvaluateFunc] = None,
        base_params: Optional[Dict[str, Any]] = None,
        is_ratio: float = 0.70,
        n_windows: Optional[int] = None,
        step_size: Optional[int] = None,
    ) -> WalkForwardResult:
        """Run walk-forward analysis delegating to :class:`WalkForwardAnalyzer`."""
        if evaluate_fn is None:
            evaluate_fn = self._default_evaluate_fn

        wfa = WalkForwardAnalyzer(
            is_ratio=is_ratio, n_windows=n_windows, step_size=step_size
        )
        return wfa.run(data, optimize_fn, evaluate_fn, base_params)

    # ------------------------------------------------------------------
    # Monte Carlo convenience
    # ------------------------------------------------------------------

    def monte_carlo(
        self,
        trades: Sequence[Trade],
        n_simulations: int = 1_000,
        seed: Optional[int] = None,
    ) -> MonteCarloResult:
        pnls = [t.pnl for t in trades]
        mc = MonteCarlo(
            initial_equity=self.cfg.initial_equity,
            seed=seed,
        )
        return mc.run(pnls, n_simulations=n_simulations)

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------

    def _simulate(self, data: pd.DataFrame) -> List[Trade]:
        trades: List[Trade] = []
        position: Optional[Dict[str, Any]] = None
        pip = self.cfg.pip_value

        for i in range(1, len(data)):
            bar = data.iloc[i]
            prev_data = data.iloc[: i + 1]

            if position is not None:
                closed, trade = self._check_exit(position, bar, i, data)
                if closed:
                    trades.append(trade)
                    position = None

            if position is None:
                signal = self.strategy.generate_signal(prev_data)
                if signal.direction == Direction.NONE:
                    continue

                slippage = self.cfg.slippage_pips * pip
                spread = self.cfg.spread_pips * pip

                if signal.direction == Direction.BUY:
                    entry = bar["close"] + spread / 2 + slippage
                    position = {
                        "direction": TradeDirection.LONG,
                        "entry_price": entry,
                        "entry_idx": i,
                        "entry_time": data.index[i],
                        "sl": signal.sl,
                        "tp": signal.tp,
                    }
                elif signal.direction == Direction.SELL:
                    entry = bar["close"] - spread / 2 - slippage
                    position = {
                        "direction": TradeDirection.SHORT,
                        "entry_price": entry,
                        "entry_idx": i,
                        "entry_time": data.index[i],
                        "sl": signal.sl,
                        "tp": signal.tp,
                    }

        if position is not None:
            last_bar = data.iloc[-1]
            trade = self._close_position(
                position, last_bar["close"], len(data) - 1, data, "end_of_data"
            )
            trades.append(trade)

        return trades

    def _check_exit(
        self,
        pos: Dict[str, Any],
        bar: pd.Series,
        bar_idx: int,
        data: pd.DataFrame,
    ) -> tuple:
        high, low, close = bar["high"], bar["low"], bar["close"]

        if pos["direction"] == TradeDirection.LONG:
            if pos["sl"] is not None and low <= pos["sl"]:
                return True, self._close_position(
                    pos, pos["sl"], bar_idx, data, "sl"
                )
            if pos["tp"] is not None and high >= pos["tp"]:
                return True, self._close_position(
                    pos, pos["tp"], bar_idx, data, "tp"
                )
        else:
            if pos["sl"] is not None and high >= pos["sl"]:
                return True, self._close_position(
                    pos, pos["sl"], bar_idx, data, "sl"
                )
            if pos["tp"] is not None and low <= pos["tp"]:
                return True, self._close_position(
                    pos, pos["tp"], bar_idx, data, "tp"
                )

        signal = self.strategy.generate_signal(data.iloc[: bar_idx + 1])
        if (
            pos["direction"] == TradeDirection.LONG
            and signal.direction == Direction.SELL
        ) or (
            pos["direction"] == TradeDirection.SHORT
            and signal.direction == Direction.BUY
        ):
            return True, self._close_position(pos, close, bar_idx, data, "signal")

        return False, None

    def _close_position(
        self,
        pos: Dict[str, Any],
        exit_price: float,
        bar_idx: int,
        data: pd.DataFrame,
        reason: str,
    ) -> Trade:
        slippage = self.cfg.slippage_pips * self.cfg.pip_value
        if pos["direction"] == TradeDirection.LONG:
            adj_exit = exit_price - slippage
            pnl = (adj_exit - pos["entry_price"]) * self.cfg.lot_size / self.cfg.pip_value
        else:
            adj_exit = exit_price + slippage
            pnl = (pos["entry_price"] - adj_exit) * self.cfg.lot_size / self.cfg.pip_value

        pnl -= self.cfg.commission_per_lot * self.cfg.lot_size
        pnl_pct = pnl / self.cfg.initial_equity * 100 if self.cfg.initial_equity else 0.0

        return Trade(
            entry_time=pos["entry_time"],
            exit_time=data.index[bar_idx],
            direction=pos["direction"],
            entry_price=pos["entry_price"],
            exit_price=adj_exit,
            sl=pos["sl"],
            tp=pos["tp"],
            pnl=pnl,
            pnl_pct=pnl_pct,
            bars_held=bar_idx - pos["entry_idx"],
            exit_reason=reason,
        )

    # ------------------------------------------------------------------
    # Equity / drawdown
    # ------------------------------------------------------------------

    def _build_equity_curve(
        self, trades: List[Trade], data: pd.DataFrame
    ) -> pd.Series:
        equity = pd.Series(self.cfg.initial_equity, index=data.index, dtype=np.float64)
        for t in trades:
            mask = equity.index >= t.exit_time
            equity.loc[mask] += t.pnl
        return equity

    @staticmethod
    def _compute_drawdown(equity: pd.Series) -> tuple:
        peak = equity.cummax()
        dd = peak - equity
        dd_pct = dd / peak.replace(0, np.nan)
        dd_pct = dd_pct.fillna(0.0)
        return dd, dd_pct

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        trades: List[Trade],
        equity: pd.Series,
        dd_pct: pd.Series,
    ) -> Dict[str, Any]:
        pnls = np.array([t.pnl for t in trades]) if trades else np.array([0.0])
        winners = pnls[pnls > 0]
        losers = pnls[pnls < 0]

        total_trades = len(trades)
        winning = int(len(winners))
        losing = int(len(losers))
        win_rate = winning / total_trades if total_trades else 0.0

        gross_profit = float(winners.sum()) if len(winners) else 0.0
        gross_loss = float(abs(losers.sum())) if len(losers) else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        total_ret = float(pnls.sum())
        total_ret_pct = total_ret / self.cfg.initial_equity * 100 if self.cfg.initial_equity else 0.0

        max_dd_pct = float(dd_pct.max())
        peak = equity.cummax()
        max_dd = float((peak - equity).max())

        avg_pnl = float(pnls.mean()) if total_trades else 0.0
        avg_winner = float(winners.mean()) if len(winners) else 0.0
        avg_loser = float(losers.mean()) if len(losers) else 0.0

        returns = equity.pct_change().dropna()
        sharpe = self._sharpe(returns)
        sortino = self._sortino(returns)
        calmar = self._calmar(total_ret_pct, max_dd_pct)

        expectancy = (
            (win_rate * avg_winner + (1 - win_rate) * avg_loser)
            if total_trades
            else 0.0
        )

        return {
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_return": total_ret,
            "total_return_pct": total_ret_pct,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "avg_trade_pnl": avg_pnl,
            "avg_winner": avg_winner,
            "avg_loser": avg_loser,
            "largest_winner": float(pnls.max()) if total_trades else 0.0,
            "largest_loser": float(pnls.min()) if total_trades else 0.0,
            "avg_bars_held": float(np.mean([t.bars_held for t in trades])) if trades else 0.0,
            "expectancy": expectancy,
        }

    def _sharpe(self, returns: pd.Series) -> float:
        if returns.empty or returns.std() == 0:
            return 0.0
        excess = returns - self.cfg.risk_free_rate / self.cfg.annualisation_factor
        return float(
            excess.mean()
            / excess.std()
            * np.sqrt(self.cfg.annualisation_factor)
        )

    def _sortino(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0
        excess = returns - self.cfg.risk_free_rate / self.cfg.annualisation_factor
        downside = excess[excess < 0]
        if downside.empty or downside.std() == 0:
            return 0.0
        return float(
            excess.mean()
            / downside.std()
            * np.sqrt(self.cfg.annualisation_factor)
        )

    @staticmethod
    def _calmar(total_return_pct: float, max_dd_pct: float) -> float:
        if max_dd_pct == 0:
            return 0.0
        return total_return_pct / (max_dd_pct * 100)

    # ------------------------------------------------------------------
    # Default WFA evaluate function
    # ------------------------------------------------------------------

    def _default_evaluate_fn(
        self, data: pd.DataFrame, params: Dict[str, Any]
    ) -> Dict[str, float]:
        self.strategy.set_parameters(params)
        result = self.run(data)
        return {
            "return": result.total_return_pct,
            "sharpe": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown_pct,
            "trades": float(result.total_trades),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare(data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        required = {"open", "high", "low", "close"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"Data missing columns: {missing}")
        if not isinstance(data.index, pd.DatetimeIndex):
            for col in ("datetime", "date", "time", "timestamp"):
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col])
                    data = data.set_index(col)
                    break
            else:
                data.index = pd.to_datetime(data.index)
        return data.sort_index()
