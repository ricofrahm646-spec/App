"""
VectorBT-Based Backtesting Engine
===================================

Vectorized backtesting engine for high-performance strategy evaluation
with multi-timeframe support, custom signals, commission, and slippage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for the vectorized backtesting engine."""

    initial_capital: float = 10000.0
    commission_pct: float = 0.0002
    commission_fixed: float = 0.0
    slippage_pct: float = 0.0001
    slippage_fixed: float = 0.0
    position_size: float = 1.0
    position_sizing_method: str = "fixed"  # 'fixed', 'percent_equity', 'kelly'
    risk_per_trade_pct: float = 1.0
    allow_short: bool = True
    max_positions: int = 1
    margin_rate: float = 1.0  # 1.0 = no leverage
    risk_free_rate: float = 0.02


@dataclass
class TradeRecord:
    """Record of a single completed trade."""

    entry_time: Any
    exit_time: Any
    direction: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    bars_held: int
    entry_signal: str = ""
    exit_signal: str = ""


@dataclass
class BacktestResult:
    """Complete backtest result container."""

    trades: List[TradeRecord]
    equity_curve: np.ndarray
    returns: np.ndarray
    positions: np.ndarray
    signals: np.ndarray
    metrics: Dict[str, float]
    config: BacktestConfig
    metadata: Dict[str, Any] = field(default_factory=dict)


class SignalGenerator:
    """Generate entry/exit signals from strategy logic or raw arrays."""

    @staticmethod
    def from_crossover(
        fast: np.ndarray, slow: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate signals from indicator crossovers."""
        n = len(fast)
        entries = np.zeros(n, dtype=np.int8)
        exits = np.zeros(n, dtype=np.int8)

        for i in range(1, n):
            if fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]:
                entries[i] = 1  # long entry
            elif fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]:
                entries[i] = -1  # short entry
                exits[i] = 1  # close long

        return entries, exits

    @staticmethod
    def from_threshold(
        indicator: np.ndarray,
        upper: float,
        lower: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate signals from threshold crossings (e.g., RSI)."""
        n = len(indicator)
        entries = np.zeros(n, dtype=np.int8)
        exits = np.zeros(n, dtype=np.int8)

        for i in range(1, n):
            if indicator[i] < lower and indicator[i - 1] >= lower:
                entries[i] = 1  # oversold → buy
            elif indicator[i] > upper and indicator[i - 1] <= upper:
                entries[i] = -1  # overbought → sell

            if indicator[i] > 50 and indicator[i - 1] <= 50 and entries[i] == 0:
                exits[i] = 1

        return entries, exits

    @staticmethod
    def from_boolean_arrays(
        buy_signals: np.ndarray,
        sell_signals: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert boolean buy/sell arrays to entry/exit signals."""
        entries = np.zeros(len(buy_signals), dtype=np.int8)
        exits = np.zeros(len(buy_signals), dtype=np.int8)

        entries[buy_signals.astype(bool)] = 1
        entries[sell_signals.astype(bool)] = -1
        exits[sell_signals.astype(bool)] = 1

        return entries, exits

    @staticmethod
    def apply_stop_loss_take_profit(
        prices: np.ndarray,
        entry_signals: np.ndarray,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ) -> np.ndarray:
        """Add exit signals based on stop-loss and take-profit levels."""
        n = len(prices)
        exit_signals = np.zeros(n, dtype=np.int8)
        position = 0
        entry_price = 0.0

        for i in range(n):
            if entry_signals[i] != 0 and position == 0:
                position = entry_signals[i]
                entry_price = prices[i]
            elif position != 0:
                if position > 0:
                    pnl_pct = (prices[i] - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - prices[i]) / entry_price

                if stop_loss_pct and pnl_pct < -stop_loss_pct:
                    exit_signals[i] = 1
                    position = 0
                elif take_profit_pct and pnl_pct > take_profit_pct:
                    exit_signals[i] = 1
                    position = 0

        return exit_signals


class VectorBTEngine:
    """
    High-performance vectorized backtesting engine.

    Simulates strategy execution on historical data with realistic
    commission, slippage, and position sizing.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    def run_backtest(
        self,
        prices: np.ndarray,
        entry_signals: np.ndarray,
        exit_signals: Optional[np.ndarray] = None,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ) -> BacktestResult:
        """
        Run a vectorized backtest.

        Args:
            prices: Close price array.
            entry_signals: Signal array (1=long, -1=short, 0=no signal).
            exit_signals: Optional exit signal array (1=exit, 0=no exit).
            high: Optional high prices for more accurate SL/TP.
            low: Optional low prices for more accurate SL/TP.
            timestamps: Optional timestamp/index array.
            stop_loss_pct: Optional stop-loss as fraction of entry price.
            take_profit_pct: Optional take-profit as fraction of entry price.

        Returns:
            BacktestResult with trades, equity curve, and performance metrics.
        """
        n = len(prices)
        if exit_signals is None:
            exit_signals = np.zeros(n, dtype=np.int8)

        if stop_loss_pct or take_profit_pct:
            sl_tp_exits = SignalGenerator.apply_stop_loss_take_profit(
                prices, entry_signals, stop_loss_pct, take_profit_pct
            )
            exit_signals = np.maximum(exit_signals, sl_tp_exits)

        if timestamps is None:
            timestamps = np.arange(n)

        equity, positions, trades, returns = self._simulate(
            prices, entry_signals, exit_signals, timestamps, high, low
        )

        metrics = self._compute_metrics(equity, returns, trades)

        return BacktestResult(
            trades=trades,
            equity_curve=equity,
            returns=returns,
            positions=positions,
            signals=entry_signals,
            metrics=metrics,
            config=self.config,
            metadata={
                "n_bars": n,
                "start_price": float(prices[0]),
                "end_price": float(prices[-1]),
            },
        )

    def run_multi_timeframe(
        self,
        data: Dict[str, Dict[str, np.ndarray]],
        signal_fn: Callable[
            [Dict[str, Dict[str, np.ndarray]]], Tuple[np.ndarray, np.ndarray]
        ],
        execution_timeframe: str = "1m",
    ) -> BacktestResult:
        """
        Run backtest with multi-timeframe data.

        Args:
            data: Dict mapping timeframe to {'close': ..., 'high': ..., ...}.
            signal_fn: Function that takes multi-TF data and returns
                       (entry_signals, exit_signals) on the execution timeframe.
            execution_timeframe: Timeframe to execute trades on.

        Returns:
            BacktestResult on the execution timeframe.
        """
        entry_signals, exit_signals = signal_fn(data)

        exec_data = data[execution_timeframe]
        prices = exec_data["close"]
        high = exec_data.get("high")
        low = exec_data.get("low")

        return self.run_backtest(
            prices=prices,
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            high=high,
            low=low,
        )

    def _simulate(
        self,
        prices: np.ndarray,
        entry_signals: np.ndarray,
        exit_signals: np.ndarray,
        timestamps: np.ndarray,
        high: Optional[np.ndarray],
        low: Optional[np.ndarray],
    ) -> Tuple[np.ndarray, np.ndarray, List[TradeRecord], np.ndarray]:
        n = len(prices)
        equity = np.zeros(n)
        positions = np.zeros(n)
        returns = np.zeros(n)

        cash = self.config.initial_capital
        position = 0.0
        direction = 0
        entry_price = 0.0
        entry_bar = 0

        trades: List[TradeRecord] = []

        equity[0] = cash

        for i in range(1, n):
            unrealized = 0.0
            if position != 0:
                if direction > 0:
                    unrealized = (prices[i] - entry_price) * position
                else:
                    unrealized = (entry_price - prices[i]) * abs(position)

            should_exit = exit_signals[i] != 0
            should_reverse = (
                entry_signals[i] != 0
                and entry_signals[i] != direction
                and position != 0
            )

            if position != 0 and (should_exit or should_reverse):
                exit_price = self._apply_slippage(prices[i], direction, exiting=True)
                commission, slippage_cost = self._compute_costs(exit_price, abs(position))

                if direction > 0:
                    trade_pnl = (exit_price - entry_price) * position - commission
                else:
                    trade_pnl = (entry_price - exit_price) * abs(position) - commission

                pnl_pct = trade_pnl / (entry_price * abs(position) + 1e-10)

                trades.append(TradeRecord(
                    entry_time=timestamps[entry_bar],
                    exit_time=timestamps[i],
                    direction="long" if direction > 0 else "short",
                    entry_price=entry_price,
                    exit_price=exit_price,
                    size=abs(position),
                    pnl=trade_pnl,
                    pnl_pct=pnl_pct,
                    commission=commission,
                    slippage=slippage_cost,
                    bars_held=i - entry_bar,
                ))

                cash += trade_pnl + entry_price * abs(position)
                position = 0.0
                direction = 0
                unrealized = 0.0

            if entry_signals[i] != 0 and position == 0:
                new_direction = int(entry_signals[i])
                if new_direction < 0 and not self.config.allow_short:
                    pass
                else:
                    size = self._compute_position_size(cash, prices[i])
                    entry_px = self._apply_slippage(prices[i], new_direction, exiting=False)
                    commission, slippage_cost = self._compute_costs(entry_px, size)

                    cost = entry_px * size + commission
                    if cost <= cash:
                        cash -= cost
                        position = size if new_direction > 0 else -size
                        direction = new_direction
                        entry_price = entry_px
                        entry_bar = i
                        unrealized = 0.0

            portfolio_value = cash + entry_price * abs(position) + unrealized
            equity[i] = portfolio_value
            returns[i] = (equity[i] - equity[i - 1]) / (equity[i - 1] + 1e-10)
            positions[i] = position

        if position != 0:
            exit_price = prices[-1]
            commission, _ = self._compute_costs(exit_price, abs(position))
            if direction > 0:
                trade_pnl = (exit_price - entry_price) * position - commission
            else:
                trade_pnl = (entry_price - exit_price) * abs(position) - commission
            pnl_pct = trade_pnl / (entry_price * abs(position) + 1e-10)
            trades.append(TradeRecord(
                entry_time=timestamps[entry_bar],
                exit_time=timestamps[-1],
                direction="long" if direction > 0 else "short",
                entry_price=entry_price,
                exit_price=exit_price,
                size=abs(position),
                pnl=trade_pnl,
                pnl_pct=pnl_pct,
                commission=commission,
                slippage=0.0,
                bars_held=n - 1 - entry_bar,
            ))

        return equity, positions, trades, returns

    def _apply_slippage(
        self, price: float, direction: int, exiting: bool
    ) -> float:
        """Apply slippage to trade execution price."""
        pct_slip = price * self.config.slippage_pct
        fixed_slip = self.config.slippage_fixed

        if (direction > 0 and not exiting) or (direction < 0 and exiting):
            return price + pct_slip + fixed_slip
        else:
            return price - pct_slip - fixed_slip

    def _compute_costs(
        self, price: float, size: float
    ) -> Tuple[float, float]:
        """Compute commission and slippage cost for a trade."""
        commission = price * size * self.config.commission_pct + self.config.commission_fixed
        slippage = price * size * self.config.slippage_pct + self.config.slippage_fixed
        return commission, slippage

    def _compute_position_size(self, equity: float, price: float) -> float:
        """Compute position size based on the sizing method."""
        if self.config.position_sizing_method == "fixed":
            return self.config.position_size
        elif self.config.position_sizing_method == "percent_equity":
            risk_amount = equity * (self.config.risk_per_trade_pct / 100.0)
            return risk_amount / (price + 1e-10)
        elif self.config.position_sizing_method == "kelly":
            return self.config.position_size
        return self.config.position_size

    def _compute_metrics(
        self,
        equity: np.ndarray,
        returns: np.ndarray,
        trades: List[TradeRecord],
    ) -> Dict[str, float]:
        """Compute comprehensive performance metrics."""
        clean_returns = returns[1:]
        clean_equity = equity[1:]

        total_return = (equity[-1] - equity[0]) / (equity[0] + 1e-10) if len(equity) > 1 else 0.0

        n_trades = len(trades)
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]

        win_rate = len(winning) / n_trades if n_trades > 0 else 0.0

        avg_win = np.mean([t.pnl for t in winning]) if winning else 0.0
        avg_loss = np.mean([abs(t.pnl) for t in losing]) if losing else 0.0
        profit_factor = (
            sum(t.pnl for t in winning) / (sum(abs(t.pnl) for t in losing) + 1e-10)
            if losing else float("inf")
        )

        max_dd, max_dd_duration = self._compute_max_drawdown(clean_equity)

        std_returns = np.std(clean_returns)
        sharpe = (
            (np.mean(clean_returns) - self.config.risk_free_rate / 252)
            / (std_returns + 1e-10)
            * np.sqrt(252)
        )

        downside = clean_returns[clean_returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else 1e-10
        sortino = (
            (np.mean(clean_returns) - self.config.risk_free_rate / 252)
            / (downside_std + 1e-10)
            * np.sqrt(252)
        )

        calmar = total_return / (abs(max_dd) + 1e-10) if max_dd != 0 else 0.0

        total_commission = sum(t.commission for t in trades)

        avg_bars = np.mean([t.bars_held for t in trades]) if trades else 0.0

        consecutive_wins, consecutive_losses = self._max_consecutive(trades)

        expectancy = (
            win_rate * avg_win - (1 - win_rate) * avg_loss
            if n_trades > 0 else 0.0
        )

        return {
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "annualized_return": self._annualize_return(total_return, len(clean_returns)),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd * 100,
            "max_drawdown_duration": max_dd_duration,
            "total_trades": n_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": expectancy,
            "avg_trade_pnl": np.mean([t.pnl for t in trades]) if trades else 0.0,
            "avg_bars_held": avg_bars,
            "max_consecutive_wins": consecutive_wins,
            "max_consecutive_losses": consecutive_losses,
            "total_commission": total_commission,
            "final_equity": equity[-1] if len(equity) > 0 else self.config.initial_capital,
            "volatility": float(std_returns * np.sqrt(252)),
        }

    @staticmethod
    def _compute_max_drawdown(equity: np.ndarray) -> Tuple[float, int]:
        if len(equity) == 0:
            return 0.0, 0

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-10)
        max_dd = float(np.max(drawdown))

        max_dd_duration = 0
        current_dd_start = 0
        in_drawdown = False

        for i in range(len(equity)):
            if equity[i] < peak[i]:
                if not in_drawdown:
                    current_dd_start = i
                    in_drawdown = True
            else:
                if in_drawdown:
                    max_dd_duration = max(max_dd_duration, i - current_dd_start)
                    in_drawdown = False

        if in_drawdown:
            max_dd_duration = max(max_dd_duration, len(equity) - current_dd_start)

        return max_dd, max_dd_duration

    @staticmethod
    def _annualize_return(total_return: float, n_periods: int, periods_per_year: int = 252) -> float:
        if n_periods == 0:
            return 0.0
        years = n_periods / periods_per_year
        if years == 0 or total_return <= -1:
            return 0.0
        return float((1 + total_return) ** (1 / years) - 1)

    @staticmethod
    def _max_consecutive(trades: List[TradeRecord]) -> Tuple[int, int]:
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for t in trades:
            if t.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses


class StrategyRunner:
    """
    Convenience class to run a strategy object through the backtest engine.
    """

    def __init__(
        self,
        engine: Optional[VectorBTEngine] = None,
        config: Optional[BacktestConfig] = None,
    ):
        self.engine = engine or VectorBTEngine(config)

    def run(
        self,
        strategy: Any,
        close: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        volume: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ) -> BacktestResult:
        """
        Run a strategy object that has check_buy_signal / check_sell_signal.

        Args:
            strategy: Object with check_buy_signal(close, high, low, volume)
                      and check_sell_signal(close, high, low, volume) methods.
            close: Close prices.
            high: Optional high prices.
            low: Optional low prices.
            volume: Optional volume data.
            timestamps: Optional timestamps.
            stop_loss_pct: Stop-loss percentage.
            take_profit_pct: Take-profit percentage.
        """
        n = len(close)
        entry_signals = np.zeros(n, dtype=np.int8)

        min_lookback = 50

        for i in range(min_lookback, n):
            window_close = close[: i + 1]
            window_high = high[: i + 1] if high is not None else None
            window_low = low[: i + 1] if low is not None else None
            window_vol = volume[: i + 1] if volume is not None else None

            try:
                if strategy.check_buy_signal(window_close, window_high, window_low, window_vol):
                    entry_signals[i] = 1
                elif strategy.check_sell_signal(window_close, window_high, window_low, window_vol):
                    entry_signals[i] = -1
            except Exception:
                continue

        return self.engine.run_backtest(
            prices=close,
            entry_signals=entry_signals,
            high=high,
            low=low,
            timestamps=timestamps,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )
