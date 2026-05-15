"""
Abstract base strategy class for the JARVIS AI Trading Operating System.

All concrete strategy implementations must inherit from BaseStrategy and
implement the abstract methods for signal generation, SL/TP calculation,
parameter retrieval, and condition validation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class SLTPLevels:
    """Stop-loss and take-profit price levels."""

    stop_loss: float
    take_profit: float
    risk_reward_ratio: float = 0.0

    def __post_init__(self) -> None:
        if self.stop_loss > 0 and self.take_profit > 0 and self.risk_reward_ratio == 0.0:
            self.risk_reward_ratio = self.take_profit / self.stop_loss


@dataclass
class TradeRecord:
    """Record of a single simulated trade."""

    entry_time: datetime
    exit_time: Optional[datetime]
    signal: Signal
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    pnl: float
    pnl_pct: float
    duration_bars: int


@dataclass
class PerformanceMetrics:
    """Aggregated performance tracking metrics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    expectancy: float = 0.0
    trade_history: List[TradeRecord] = field(default_factory=list)

    def update_from_trades(self, trades: List[TradeRecord]) -> None:
        """Recalculate all metrics from a list of trade records."""
        self.trade_history = trades
        self.total_trades = len(trades)

        if self.total_trades == 0:
            return

        pnls = np.array([t.pnl for t in trades])
        wins = pnls[pnls > 0]
        losses = pnls[pnls <= 0]

        self.winning_trades = len(wins)
        self.losing_trades = len(losses)
        self.total_pnl = float(np.sum(pnls))
        self.total_pnl_pct = float(np.sum([t.pnl_pct for t in trades]))

        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        self.avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        self.avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0

        gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
        gross_loss = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0
        self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

        self.max_consecutive_wins = self._max_consecutive(pnls, positive=True)
        self.max_consecutive_losses = self._max_consecutive(pnls, positive=False)

        self._calculate_drawdown(pnls)

        if len(pnls) > 1:
            mean_return = float(np.mean(pnls))
            std_return = float(np.std(pnls, ddof=1))
            self.sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0

            downside = pnls[pnls < 0]
            downside_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 0.0
            self.sortino_ratio = (mean_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

        self.expectancy = (
            self.win_rate * self.avg_win + (1 - self.win_rate) * self.avg_loss
        )

    @staticmethod
    def _max_consecutive(pnls: np.ndarray, positive: bool) -> int:
        """Count the longest consecutive winning or losing streak."""
        max_run = 0
        current_run = 0
        for p in pnls:
            if (positive and p > 0) or (not positive and p <= 0):
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        return max_run

    def _calculate_drawdown(self, pnls: np.ndarray) -> None:
        """Calculate maximum drawdown from PnL series."""
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        self.max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

        if len(peak) > 0:
            peak_nonzero = np.where(peak > 0, peak, 1.0)
            dd_pct = drawdown / peak_nonzero
            self.max_drawdown_pct = float(np.max(dd_pct)) * 100.0


class BaseStrategy(ABC):
    """Abstract base class for all JARVIS trading strategies.

    Every concrete strategy must implement the four abstract methods:
    - generate_signal: Produce a BUY/SELL/HOLD signal from market data.
    - calculate_sl_tp: Determine stop-loss and take-profit levels.
    - get_parameters: Return the strategy's configurable parameters.
    - validate_conditions: Check if market conditions are suitable.

    The base class provides performance tracking via the `metrics` attribute,
    a backtest runner, and common utility methods for technical analysis.
    """

    def __init__(self, name: str, timeframe: str = "H1") -> None:
        self.name = name
        self.timeframe = timeframe
        self.metrics = PerformanceMetrics()
        self._is_initialized = False

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        """Analyze market data and produce a trading signal.

        Args:
            data: OHLCV DataFrame with columns: open, high, low, close, volume.
                  Index should be datetime. Most recent bar is the last row.

        Returns:
            Signal.BUY, Signal.SELL, or Signal.HOLD.
        """

    @abstractmethod
    def calculate_sl_tp(self, signal: Signal, data: pd.DataFrame) -> SLTPLevels:
        """Calculate stop-loss and take-profit price levels for a given signal.

        Args:
            signal: The BUY or SELL signal to calculate levels for.
            data: OHLCV DataFrame with current market data.

        Returns:
            SLTPLevels with stop_loss and take_profit values in price distance
            (not absolute price).
        """

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return a dictionary of all configurable strategy parameters.

        Returns:
            Dict mapping parameter names to their current values.
        """

    @abstractmethod
    def validate_conditions(self, data: pd.DataFrame) -> bool:
        """Check if current market conditions are suitable for this strategy.

        Args:
            data: OHLCV DataFrame with current market data.

        Returns:
            True if conditions are valid for trading, False otherwise.
        """

    def backtest(
        self,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        risk_per_trade: float = 0.01,
    ) -> PerformanceMetrics:
        """Run a simple bar-by-bar backtest on historical data.

        Args:
            data: OHLCV DataFrame with columns: open, high, low, close, volume.
            initial_balance: Starting account balance.
            risk_per_trade: Fraction of balance risked per trade (e.g., 0.01 = 1%).

        Returns:
            PerformanceMetrics with full trade history and calculated statistics.
        """
        trades: List[TradeRecord] = []
        balance = initial_balance
        min_bars = self._get_min_bars()

        in_trade = False
        entry_price = 0.0
        entry_idx = 0
        current_signal = Signal.HOLD
        current_sl = 0.0
        current_tp = 0.0

        for i in range(min_bars, len(data)):
            window = data.iloc[: i + 1]
            current_close = float(data.iloc[i]["close"])

            if in_trade:
                hit_sl, hit_tp = self._check_sl_tp(
                    current_signal, entry_price, current_sl, current_tp,
                    float(data.iloc[i]["high"]), float(data.iloc[i]["low"]),
                )

                if hit_sl or hit_tp:
                    if hit_tp:
                        exit_price = (
                            entry_price + current_tp
                            if current_signal == Signal.BUY
                            else entry_price - current_tp
                        )
                    else:
                        exit_price = (
                            entry_price - current_sl
                            if current_signal == Signal.BUY
                            else entry_price + current_sl
                        )

                    pnl = self._calculate_pnl(
                        current_signal, entry_price, exit_price, balance, risk_per_trade
                    )
                    trades.append(TradeRecord(
                        entry_time=data.index[entry_idx],
                        exit_time=data.index[i],
                        signal=current_signal,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        stop_loss=current_sl,
                        take_profit=current_tp,
                        pnl=pnl,
                        pnl_pct=pnl / balance * 100.0,
                        duration_bars=i - entry_idx,
                    ))
                    balance += pnl
                    in_trade = False
                continue

            if not self.validate_conditions(window):
                continue

            signal = self.generate_signal(window)
            if signal == Signal.HOLD:
                continue

            sl_tp = self.calculate_sl_tp(signal, window)
            entry_price = current_close
            entry_idx = i
            current_signal = signal
            current_sl = sl_tp.stop_loss
            current_tp = sl_tp.take_profit
            in_trade = True

        self.metrics.update_from_trades(trades)
        return self.metrics

    def _get_min_bars(self) -> int:
        """Minimum number of bars needed before the strategy can generate signals."""
        return 50

    @staticmethod
    def _check_sl_tp(
        signal: Signal,
        entry: float,
        sl: float,
        tp: float,
        bar_high: float,
        bar_low: float,
    ) -> Tuple[bool, bool]:
        """Check if a bar triggered SL or TP."""
        if signal == Signal.BUY:
            hit_sl = sl > 0 and bar_low <= entry - sl
            hit_tp = tp > 0 and bar_high >= entry + tp
        else:
            hit_sl = sl > 0 and bar_high >= entry + sl
            hit_tp = tp > 0 and bar_low <= entry - tp

        if hit_sl and hit_tp:
            return True, False

        return hit_sl, hit_tp

    @staticmethod
    def _calculate_pnl(
        signal: Signal,
        entry_price: float,
        exit_price: float,
        balance: float,
        risk_fraction: float,
    ) -> float:
        """Calculate trade PnL based on direction and risk sizing."""
        position_size = balance * risk_fraction
        if signal == Signal.BUY:
            return position_size * (exit_price - entry_price) / entry_price
        else:
            return position_size * (entry_price - exit_price) / entry_price

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return series.rolling(window=period).mean()

    @staticmethod
    def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range."""
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        return tr.rolling(window=period).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.finfo(float).eps)
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def bollinger_bands(
        series: pd.Series, period: int = 20, std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands: returns (upper, middle, lower)."""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower

    @staticmethod
    def macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD: returns (macd_line, signal_line, histogram)."""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def adx(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average Directional Index."""
        high = data["high"]
        low = data["low"]
        close = data["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr_val = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr_val.replace(0, np.finfo(float).eps)
        minus_di = 100 * minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr_val.replace(0, np.finfo(float).eps)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.finfo(float).eps)
        adx_val = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        return adx_val

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', timeframe='{self.timeframe}')"
