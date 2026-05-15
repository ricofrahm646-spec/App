"""
Performance Analytics
======================

Full performance report generation with equity curve analysis, drawdown
analysis, trade distribution, time-based returns breakdown, and
statistical significance tests.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TradeData:
    """Standardized trade data for performance analysis."""

    pnl: float
    pnl_pct: float
    entry_time: float  # unix timestamp or ordinal
    exit_time: float
    direction: str  # 'long' or 'short'
    size: float
    entry_price: float
    exit_price: float
    bars_held: int = 0
    commission: float = 0.0


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""

    summary: Dict[str, float]
    equity_analysis: Dict[str, Any]
    drawdown_analysis: Dict[str, Any]
    trade_analysis: Dict[str, Any]
    returns_breakdown: Dict[str, Any]
    statistical_tests: Dict[str, Any]
    risk_metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class EquityCurveAnalyzer:
    """Analyze equity curve characteristics."""

    def analyze(
        self,
        equity: np.ndarray,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Comprehensive equity curve analysis.

        Args:
            equity: Array of portfolio equity values.
            risk_free_rate: Annual risk-free rate for ratio calculations.
        """
        n = len(equity)
        if n < 2:
            return {"error": "Insufficient data"}

        returns = np.diff(equity) / (equity[:-1] + 1e-10)
        log_returns = np.log(equity[1:] / (equity[:-1] + 1e-10))

        total_return = (equity[-1] - equity[0]) / (equity[0] + 1e-10)

        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf

        volatility = float(np.std(returns) * np.sqrt(252))
        sharpe = float(np.mean(excess_returns) / (np.std(returns) + 1e-10) * np.sqrt(252))

        downside_returns = returns[returns < 0]
        downside_vol = float(np.std(downside_returns) * np.sqrt(252)) if len(downside_returns) > 0 else 1e-10
        sortino = float(np.mean(excess_returns) / (downside_vol / np.sqrt(252) + 1e-10) * np.sqrt(252))

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-10)
        max_dd = float(np.max(drawdown))
        calmar = float(total_return / (max_dd + 1e-10))

        omega = self._omega_ratio(returns, threshold=0.0)

        trend = self._linear_regression(np.arange(n), equity)

        underwater_periods = self._underwater_analysis(equity, peak)

        rolling_sharpe_30 = self._rolling_sharpe(returns, window=30)
        rolling_sharpe_90 = self._rolling_sharpe(returns, window=90)

        return {
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "annualized_return": self._annualize_return(total_return, n),
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "omega_ratio": omega,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd * 100,
            "skewness": float(self._skewness(returns)),
            "kurtosis": float(self._kurtosis(returns)),
            "positive_days_ratio": float(np.mean(returns > 0)),
            "best_day": float(np.max(returns)),
            "worst_day": float(np.min(returns)),
            "avg_daily_return": float(np.mean(returns)),
            "daily_return_std": float(np.std(returns)),
            "trend_slope": trend["slope"],
            "trend_r_squared": trend["r_squared"],
            "underwater_periods": underwater_periods,
            "rolling_sharpe_30": rolling_sharpe_30.tolist() if len(rolling_sharpe_30) > 0 else [],
            "rolling_sharpe_90": rolling_sharpe_90.tolist() if len(rolling_sharpe_90) > 0 else [],
            "equity_start": float(equity[0]),
            "equity_end": float(equity[-1]),
            "equity_peak": float(np.max(equity)),
            "equity_trough": float(np.min(equity)),
        }

    @staticmethod
    def _omega_ratio(returns: np.ndarray, threshold: float = 0.0) -> float:
        excess = returns - threshold
        sum_positive = np.sum(excess[excess > 0])
        sum_negative = np.sum(np.abs(excess[excess < 0]))
        if sum_negative == 0:
            return float("inf") if sum_positive > 0 else 1.0
        return float(sum_positive / sum_negative)

    @staticmethod
    def _rolling_sharpe(returns: np.ndarray, window: int = 30) -> np.ndarray:
        n = len(returns)
        if n < window:
            return np.array([])
        result = np.zeros(n - window + 1)
        for i in range(len(result)):
            w = returns[i:i + window]
            result[i] = np.mean(w) / (np.std(w) + 1e-10) * np.sqrt(252)
        return result

    @staticmethod
    def _underwater_analysis(
        equity: np.ndarray, peak: np.ndarray
    ) -> Dict[str, Any]:
        in_dd = equity < peak
        n_underwater = int(np.sum(in_dd))
        pct_underwater = float(n_underwater / len(equity))

        periods: List[int] = []
        current = 0
        for underwater in in_dd:
            if underwater:
                current += 1
            else:
                if current > 0:
                    periods.append(current)
                current = 0
        if current > 0:
            periods.append(current)

        return {
            "pct_time_underwater": pct_underwater,
            "avg_underwater_duration": float(np.mean(periods)) if periods else 0.0,
            "max_underwater_duration": int(np.max(periods)) if periods else 0,
            "n_drawdown_periods": len(periods),
        }

    @staticmethod
    def _linear_regression(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        x_f = x.astype(np.float64)
        y_f = y.astype(np.float64)
        x_mean = x_f.mean()
        y_mean = y_f.mean()
        ss_xx = np.sum((x_f - x_mean) ** 2)
        if ss_xx == 0:
            return {"slope": 0.0, "r_squared": 0.0}
        slope = float(np.sum((x_f - x_mean) * (y_f - y_mean)) / ss_xx)
        y_pred = y_mean + slope * (x_f - x_mean)
        ss_res = np.sum((y_f - y_pred) ** 2)
        ss_tot = np.sum((y_f - y_mean) ** 2)
        r_sq = float(1.0 - ss_res / (ss_tot + 1e-10)) if ss_tot > 0 else 0.0
        return {"slope": slope, "r_squared": max(0.0, r_sq)}

    @staticmethod
    def _annualize_return(total_return: float, n_periods: int, periods_per_year: int = 252) -> float:
        if n_periods == 0 or total_return <= -1:
            return 0.0
        years = n_periods / periods_per_year
        return float((1 + total_return) ** (1 / max(years, 0.01)) - 1)

    @staticmethod
    def _skewness(arr: np.ndarray) -> float:
        n = len(arr)
        if n < 3:
            return 0.0
        m = np.mean(arr)
        s = np.std(arr)
        if s < 1e-10:
            return 0.0
        return float(np.mean(((arr - m) / s) ** 3))

    @staticmethod
    def _kurtosis(arr: np.ndarray) -> float:
        n = len(arr)
        if n < 4:
            return 0.0
        m = np.mean(arr)
        s = np.std(arr)
        if s < 1e-10:
            return 0.0
        return float(np.mean(((arr - m) / s) ** 4) - 3.0)


class DrawdownAnalyzer:
    """Detailed drawdown analysis."""

    def analyze(self, equity: np.ndarray) -> Dict[str, Any]:
        """Analyze all drawdown events in the equity curve."""
        n = len(equity)
        if n < 2:
            return {"error": "Insufficient data"}

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-10)

        dd_events = self._extract_drawdown_events(equity, peak, drawdown)
        dd_events.sort(key=lambda x: x["depth"], reverse=True)

        top_5 = dd_events[:5] if len(dd_events) >= 5 else dd_events

        depths = [e["depth"] for e in dd_events] if dd_events else [0.0]

        return {
            "max_drawdown": float(np.max(drawdown)),
            "max_drawdown_pct": float(np.max(drawdown) * 100),
            "avg_drawdown": float(np.mean(depths)),
            "avg_drawdown_pct": float(np.mean(depths) * 100),
            "n_drawdown_events": len(dd_events),
            "top_5_drawdowns": top_5,
            "current_drawdown": float(drawdown[-1]),
            "current_drawdown_pct": float(drawdown[-1] * 100),
            "time_to_recovery_avg": float(
                np.mean([e["recovery_bars"] for e in dd_events if e["recovered"]])
            ) if any(e["recovered"] for e in dd_events) else float("inf"),
            "drawdown_series": drawdown.tolist(),
            "depth_distribution": {
                "under_5pct": sum(1 for d in depths if d < 0.05),
                "5_to_10pct": sum(1 for d in depths if 0.05 <= d < 0.10),
                "10_to_20pct": sum(1 for d in depths if 0.10 <= d < 0.20),
                "20_to_30pct": sum(1 for d in depths if 0.20 <= d < 0.30),
                "over_30pct": sum(1 for d in depths if d >= 0.30),
            },
        }

    @staticmethod
    def _extract_drawdown_events(
        equity: np.ndarray, peak: np.ndarray, drawdown: np.ndarray
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        n = len(equity)
        i = 0

        while i < n:
            if drawdown[i] > 0:
                start = i
                max_depth = drawdown[i]
                max_depth_idx = i

                while i < n and drawdown[i] > 0:
                    if drawdown[i] > max_depth:
                        max_depth = drawdown[i]
                        max_depth_idx = i
                    i += 1

                recovery_idx = i if i < n else -1
                recovered = recovery_idx > 0

                events.append({
                    "start_idx": start,
                    "trough_idx": max_depth_idx,
                    "end_idx": recovery_idx if recovered else n - 1,
                    "depth": float(max_depth),
                    "depth_pct": float(max_depth * 100),
                    "duration_bars": max_depth_idx - start,
                    "recovery_bars": (recovery_idx - max_depth_idx) if recovered else -1,
                    "total_bars": (recovery_idx - start) if recovered else (n - 1 - start),
                    "recovered": recovered,
                    "peak_equity": float(peak[start]),
                    "trough_equity": float(equity[max_depth_idx]),
                })
            else:
                i += 1

        return events


class TradeAnalyzer:
    """Analyze trade characteristics and distributions."""

    def analyze(self, trades: List[TradeData]) -> Dict[str, Any]:
        """Comprehensive trade analysis."""
        if not trades:
            return {"error": "No trades to analyze"}

        pnls = np.array([t.pnl for t in trades])
        pnl_pcts = np.array([t.pnl_pct for t in trades])
        bars_held = np.array([t.bars_held for t in trades])

        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]
        longs = [t for t in trades if t.direction == "long"]
        shorts = [t for t in trades if t.direction == "short"]

        win_rate = len(winners) / len(trades)
        avg_win = float(np.mean([t.pnl for t in winners])) if winners else 0.0
        avg_loss = float(np.mean([abs(t.pnl) for t in losers])) if losers else 0.0

        payoff_ratio = avg_win / (avg_loss + 1e-10)
        expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss

        total_gross_profit = sum(t.pnl for t in winners)
        total_gross_loss = sum(abs(t.pnl) for t in losers)
        profit_factor = total_gross_profit / (total_gross_loss + 1e-10)

        consecutive = self._consecutive_analysis(trades)
        streak = self._streak_analysis(trades)

        long_analysis = self._direction_analysis(longs, "long")
        short_analysis = self._direction_analysis(shorts, "short")

        return {
            "total_trades": len(trades),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": win_rate,
            "loss_rate": 1 - win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": float(np.max(pnls)),
            "largest_loss": float(np.min(pnls)),
            "avg_trade_pnl": float(np.mean(pnls)),
            "median_trade_pnl": float(np.median(pnls)),
            "std_trade_pnl": float(np.std(pnls)),
            "total_pnl": float(np.sum(pnls)),
            "payoff_ratio": payoff_ratio,
            "expectancy": expectancy,
            "profit_factor": profit_factor,
            "total_gross_profit": total_gross_profit,
            "total_gross_loss": total_gross_loss,
            "total_commission": sum(t.commission for t in trades),
            "avg_bars_held": float(np.mean(bars_held)),
            "avg_winner_bars": float(np.mean([t.bars_held for t in winners])) if winners else 0.0,
            "avg_loser_bars": float(np.mean([t.bars_held for t in losers])) if losers else 0.0,
            "max_bars_held": int(np.max(bars_held)),
            "pnl_percentiles": {
                p: float(np.percentile(pnls, p))
                for p in [5, 10, 25, 50, 75, 90, 95]
            },
            "consecutive": consecutive,
            "streaks": streak,
            "long_trades": long_analysis,
            "short_trades": short_analysis,
            "pnl_distribution": {
                "skewness": float(self._skewness(pnls)),
                "kurtosis": float(self._kurtosis(pnls)),
                "jarque_bera": self._jarque_bera(pnls),
            },
        }

    @staticmethod
    def _consecutive_analysis(trades: List[TradeData]) -> Dict[str, int]:
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0

        for t in trades:
            if t.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)

        return {
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
        }

    @staticmethod
    def _streak_analysis(trades: List[TradeData]) -> Dict[str, Any]:
        streaks: List[Dict[str, Any]] = []
        if not trades:
            return {"win_streaks": [], "loss_streaks": []}

        current_type = "win" if trades[0].pnl > 0 else "loss"
        current_length = 1
        current_pnl = trades[0].pnl

        for t in trades[1:]:
            t_type = "win" if t.pnl > 0 else "loss"
            if t_type == current_type:
                current_length += 1
                current_pnl += t.pnl
            else:
                streaks.append({
                    "type": current_type,
                    "length": current_length,
                    "total_pnl": current_pnl,
                })
                current_type = t_type
                current_length = 1
                current_pnl = t.pnl

        streaks.append({
            "type": current_type,
            "length": current_length,
            "total_pnl": current_pnl,
        })

        win_streaks = sorted(
            [s for s in streaks if s["type"] == "win"],
            key=lambda s: s["length"], reverse=True,
        )[:5]
        loss_streaks = sorted(
            [s for s in streaks if s["type"] == "loss"],
            key=lambda s: s["length"], reverse=True,
        )[:5]

        return {"win_streaks": win_streaks, "loss_streaks": loss_streaks}

    @staticmethod
    def _direction_analysis(
        trades: List[TradeData], direction: str
    ) -> Dict[str, Any]:
        if not trades:
            return {
                "count": 0, "win_rate": 0.0,
                "avg_pnl": 0.0, "total_pnl": 0.0,
            }

        pnls = [t.pnl for t in trades]
        winners = [t for t in trades if t.pnl > 0]

        return {
            "count": len(trades),
            "win_rate": len(winners) / len(trades),
            "avg_pnl": float(np.mean(pnls)),
            "total_pnl": float(np.sum(pnls)),
            "avg_bars_held": float(np.mean([t.bars_held for t in trades])),
        }

    @staticmethod
    def _skewness(arr: np.ndarray) -> float:
        if len(arr) < 3:
            return 0.0
        m, s = np.mean(arr), np.std(arr)
        if s < 1e-10:
            return 0.0
        return float(np.mean(((arr - m) / s) ** 3))

    @staticmethod
    def _kurtosis(arr: np.ndarray) -> float:
        if len(arr) < 4:
            return 0.0
        m, s = np.mean(arr), np.std(arr)
        if s < 1e-10:
            return 0.0
        return float(np.mean(((arr - m) / s) ** 4) - 3.0)

    @staticmethod
    def _jarque_bera(arr: np.ndarray) -> Dict[str, float]:
        n = len(arr)
        if n < 4:
            return {"statistic": 0.0, "p_value": 1.0, "is_normal": True}
        m, s = np.mean(arr), np.std(arr)
        if s < 1e-10:
            return {"statistic": 0.0, "p_value": 1.0, "is_normal": True}
        skew = float(np.mean(((arr - m) / s) ** 3))
        kurt = float(np.mean(((arr - m) / s) ** 4) - 3.0)
        jb = n / 6 * (skew ** 2 + kurt ** 2 / 4)
        p_value = float(np.exp(-jb / 2)) if jb < 50 else 0.0
        return {
            "statistic": float(jb),
            "p_value": p_value,
            "is_normal": p_value > 0.05,
        }


class ReturnsBreakdown:
    """Break down returns by time period (daily, weekly, monthly)."""

    def analyze(
        self,
        equity: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        bars_per_day: int = 1,
    ) -> Dict[str, Any]:
        """
        Compute returns breakdown by different time periods.

        Args:
            equity: Equity curve array.
            timestamps: Optional timestamp array (unix timestamps).
            bars_per_day: Number of bars per trading day.
        """
        daily_returns = self._compute_period_returns(equity, bars_per_day)
        weekly_returns = self._compute_period_returns(equity, bars_per_day * 5)
        monthly_returns = self._compute_period_returns(equity, bars_per_day * 21)

        result: Dict[str, Any] = {
            "daily": self._returns_stats(daily_returns, "daily"),
            "weekly": self._returns_stats(weekly_returns, "weekly"),
            "monthly": self._returns_stats(monthly_returns, "monthly"),
        }

        if timestamps is not None and len(timestamps) > 0:
            calendar_monthly = self._calendar_monthly_returns(equity, timestamps)
            result["calendar_monthly"] = calendar_monthly

        result["distribution"] = {
            "daily_histogram": self._histogram(daily_returns, 20),
            "best_periods": {
                "best_day": float(np.max(daily_returns)) if len(daily_returns) > 0 else 0.0,
                "best_week": float(np.max(weekly_returns)) if len(weekly_returns) > 0 else 0.0,
                "best_month": float(np.max(monthly_returns)) if len(monthly_returns) > 0 else 0.0,
            },
            "worst_periods": {
                "worst_day": float(np.min(daily_returns)) if len(daily_returns) > 0 else 0.0,
                "worst_week": float(np.min(weekly_returns)) if len(weekly_returns) > 0 else 0.0,
                "worst_month": float(np.min(monthly_returns)) if len(monthly_returns) > 0 else 0.0,
            },
        }

        return result

    @staticmethod
    def _compute_period_returns(
        equity: np.ndarray, period_length: int
    ) -> np.ndarray:
        if len(equity) < period_length + 1:
            return np.array([])
        indices = np.arange(0, len(equity), period_length)
        if indices[-1] != len(equity) - 1:
            indices = np.append(indices, len(equity) - 1)
        period_equity = equity[indices]
        returns = np.diff(period_equity) / (period_equity[:-1] + 1e-10)
        return returns

    @staticmethod
    def _returns_stats(returns: np.ndarray, period_name: str) -> Dict[str, float]:
        if len(returns) == 0:
            return {"n_periods": 0}
        return {
            "n_periods": len(returns),
            "mean_return": float(np.mean(returns)),
            "median_return": float(np.median(returns)),
            "std_return": float(np.std(returns)),
            "min_return": float(np.min(returns)),
            "max_return": float(np.max(returns)),
            "positive_ratio": float(np.mean(returns > 0)),
            "total_return": float(np.prod(1 + returns) - 1),
        }

    @staticmethod
    def _calendar_monthly_returns(
        equity: np.ndarray, timestamps: np.ndarray
    ) -> Dict[str, Dict[str, float]]:
        """Compute returns grouped by calendar month."""
        result: Dict[str, Dict[str, float]] = {}

        try:
            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
        except (OSError, ValueError):
            dates = [datetime(2020, 1, 1) + timedelta(days=int(ts)) for ts in timestamps]

        month_groups: Dict[str, List[int]] = {}
        for i, dt in enumerate(dates):
            key = f"{dt.year}-{dt.month:02d}"
            month_groups.setdefault(key, []).append(i)

        for month_key, indices in sorted(month_groups.items()):
            if len(indices) < 2:
                continue
            start_eq = equity[indices[0]]
            end_eq = equity[indices[-1]]
            monthly_return = (end_eq - start_eq) / (start_eq + 1e-10)
            result[month_key] = {
                "return": float(monthly_return),
                "return_pct": float(monthly_return * 100),
                "start_equity": float(start_eq),
                "end_equity": float(end_eq),
                "n_bars": len(indices),
            }

        return result

    @staticmethod
    def _histogram(
        data: np.ndarray, n_bins: int = 20
    ) -> Dict[str, Any]:
        if len(data) == 0:
            return {"bins": [], "counts": []}
        counts, bin_edges = np.histogram(data, bins=n_bins)
        return {
            "bins": bin_edges.tolist(),
            "counts": counts.tolist(),
        }


class StatisticalTests:
    """Statistical significance tests for strategy performance."""

    def run_all_tests(
        self,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Run a suite of statistical tests on strategy returns.

        Args:
            returns: Strategy return series.
            benchmark_returns: Optional benchmark returns for comparison.
        """
        results: Dict[str, Any] = {}

        results["t_test"] = self._t_test(returns)
        results["sharpe_significance"] = self._sharpe_significance(returns)
        results["runs_test"] = self._runs_test(returns)
        results["autocorrelation"] = self._autocorrelation_test(returns)

        if benchmark_returns is not None:
            min_len = min(len(returns), len(benchmark_returns))
            results["vs_benchmark"] = self._benchmark_comparison(
                returns[:min_len], benchmark_returns[:min_len]
            )

        results["stationarity"] = self._adf_approximation(returns)

        return results

    @staticmethod
    def _t_test(returns: np.ndarray) -> Dict[str, float]:
        """Test if mean return is significantly different from zero."""
        n = len(returns)
        if n < 3:
            return {"statistic": 0.0, "p_value": 1.0, "significant": False}

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        se = std / np.sqrt(n)
        t_stat = mean / (se + 1e-10)

        df = n - 1
        p_value = 2.0 * (1.0 - min(0.9999, 0.5 + 0.5 * np.tanh(abs(t_stat) / np.sqrt(2))))

        return {
            "statistic": float(t_stat),
            "p_value": float(p_value),
            "significant": p_value < 0.05,
            "mean_return": float(mean),
            "std_error": float(se),
        }

    @staticmethod
    def _sharpe_significance(
        returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> Dict[str, float]:
        """Test if the Sharpe ratio is statistically significant."""
        n = len(returns)
        if n < 30:
            return {"sharpe": 0.0, "p_value": 1.0, "significant": False}

        daily_rf = risk_free_rate / 252
        excess = returns - daily_rf
        sharpe = float(np.mean(excess) / (np.std(returns) + 1e-10) * np.sqrt(252))

        se_sharpe = np.sqrt((1 + 0.5 * sharpe ** 2) / n)
        z_stat = sharpe / (se_sharpe + 1e-10)
        p_value = 2.0 * (1.0 - min(0.9999, 0.5 + 0.5 * np.tanh(abs(z_stat) / np.sqrt(2))))

        return {
            "sharpe": sharpe,
            "standard_error": float(se_sharpe),
            "z_statistic": float(z_stat),
            "p_value": float(p_value),
            "significant": p_value < 0.05,
        }

    @staticmethod
    def _runs_test(returns: np.ndarray) -> Dict[str, Any]:
        """
        Wald-Wolfowitz runs test for randomness.

        Tests if the sequence of positive/negative returns is random.
        """
        n = len(returns)
        if n < 10:
            return {"statistic": 0.0, "p_value": 1.0, "is_random": True}

        signs = np.sign(returns)
        signs[signs == 0] = 1
        n_pos = int(np.sum(signs > 0))
        n_neg = int(np.sum(signs < 0))

        runs = 1
        for i in range(1, n):
            if signs[i] != signs[i - 1]:
                runs += 1

        expected_runs = 1 + 2 * n_pos * n_neg / (n_pos + n_neg + 1e-10)
        var_runs = (
            2 * n_pos * n_neg * (2 * n_pos * n_neg - n_pos - n_neg)
            / ((n_pos + n_neg) ** 2 * (n_pos + n_neg - 1) + 1e-10)
        )

        if var_runs > 0:
            z = (runs - expected_runs) / np.sqrt(var_runs)
        else:
            z = 0.0

        p_value = 2.0 * (1.0 - min(0.9999, 0.5 + 0.5 * np.tanh(abs(z) / np.sqrt(2))))

        return {
            "n_runs": runs,
            "expected_runs": float(expected_runs),
            "z_statistic": float(z),
            "p_value": float(p_value),
            "is_random": p_value > 0.05,
        }

    @staticmethod
    def _autocorrelation_test(
        returns: np.ndarray, max_lag: int = 10
    ) -> Dict[str, Any]:
        """Test for autocorrelation in returns at various lags."""
        n = len(returns)
        if n < max_lag + 5:
            return {"lags": {}, "has_autocorrelation": False}

        mean = np.mean(returns)
        var = np.var(returns)
        if var < 1e-10:
            return {"lags": {}, "has_autocorrelation": False}

        lags: Dict[int, Dict[str, float]] = {}
        significant_count = 0
        threshold = 1.96 / np.sqrt(n)

        for lag in range(1, min(max_lag + 1, n)):
            ac = np.sum((returns[lag:] - mean) * (returns[:-lag] - mean)) / (n * var)
            is_sig = abs(ac) > threshold
            if is_sig:
                significant_count += 1
            lags[lag] = {
                "autocorrelation": float(ac),
                "significant": is_sig,
            }

        return {
            "lags": lags,
            "threshold": float(threshold),
            "has_autocorrelation": significant_count > max_lag * 0.3,
            "n_significant_lags": significant_count,
        }

    @staticmethod
    def _benchmark_comparison(
        returns: np.ndarray, benchmark_returns: np.ndarray
    ) -> Dict[str, float]:
        """Compare strategy returns against a benchmark."""
        excess = returns - benchmark_returns
        n = len(excess)

        alpha = float(np.mean(excess))
        tracking_error = float(np.std(excess) * np.sqrt(252))
        info_ratio = alpha * 252 / (tracking_error + 1e-10)

        beta = float(
            np.cov(returns, benchmark_returns)[0, 1]
            / (np.var(benchmark_returns) + 1e-10)
        )

        correlation = float(np.corrcoef(returns, benchmark_returns)[0, 1])

        up_markets = benchmark_returns > 0
        down_markets = benchmark_returns <= 0

        up_capture = (
            float(np.mean(returns[up_markets]) / (np.mean(benchmark_returns[up_markets]) + 1e-10))
            if np.any(up_markets) else 0.0
        )
        down_capture = (
            float(np.mean(returns[down_markets]) / (np.mean(benchmark_returns[down_markets]) + 1e-10))
            if np.any(down_markets) else 0.0
        )

        return {
            "alpha_daily": alpha,
            "alpha_annualized": alpha * 252,
            "beta": beta,
            "correlation": correlation,
            "tracking_error": tracking_error,
            "information_ratio": info_ratio,
            "up_capture_ratio": up_capture,
            "down_capture_ratio": down_capture,
        }

    @staticmethod
    def _adf_approximation(returns: np.ndarray) -> Dict[str, Any]:
        """Approximate Augmented Dickey-Fuller test for stationarity."""
        n = len(returns)
        if n < 20:
            return {"is_stationary": True, "message": "Too few data points"}

        cumulative = np.cumsum(returns)
        y = cumulative[1:]
        x = cumulative[:-1]

        x_mean = np.mean(x)
        y_mean = np.mean(y)
        ss_xx = np.sum((x - x_mean) ** 2)
        if ss_xx == 0:
            return {"is_stationary": True, "rho": 1.0}

        rho = np.sum((x - x_mean) * (y - y_mean)) / ss_xx
        residuals = y - (y_mean + rho * (x - x_mean))
        sse = np.sum(residuals ** 2) / (n - 2)
        se_rho = np.sqrt(sse / (ss_xx + 1e-10))
        t_stat = (rho - 1) / (se_rho + 1e-10)

        critical_values = {1: -3.43, 5: -2.86, 10: -2.57}
        is_stationary = t_stat < critical_values[5]

        return {
            "t_statistic": float(t_stat),
            "rho": float(rho),
            "critical_values": critical_values,
            "is_stationary": is_stationary,
        }


class PerformanceAnalyzer:
    """
    Unified performance analysis engine that generates comprehensive
    reports from equity curves and trade data.
    """

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.equity_analyzer = EquityCurveAnalyzer()
        self.drawdown_analyzer = DrawdownAnalyzer()
        self.trade_analyzer = TradeAnalyzer()
        self.returns_breakdown = ReturnsBreakdown()
        self.statistical_tests = StatisticalTests()

    def generate_report(
        self,
        equity: np.ndarray,
        trades: Optional[List[TradeData]] = None,
        timestamps: Optional[np.ndarray] = None,
        benchmark_returns: Optional[np.ndarray] = None,
        bars_per_day: int = 1,
    ) -> PerformanceReport:
        """
        Generate a full performance report.

        Args:
            equity: Portfolio equity curve.
            trades: Optional list of TradeData objects.
            timestamps: Optional timestamp array.
            benchmark_returns: Optional benchmark return series.
            bars_per_day: Number of bars per trading day.

        Returns:
            PerformanceReport with all analysis sections.
        """
        equity = np.asarray(equity, dtype=np.float64)
        returns = np.diff(equity) / (equity[:-1] + 1e-10)

        equity_analysis = self.equity_analyzer.analyze(equity, self.risk_free_rate)

        drawdown_analysis = self.drawdown_analyzer.analyze(equity)

        trade_analysis = {}
        if trades:
            trade_analysis = self.trade_analyzer.analyze(trades)

        returns_analysis = self.returns_breakdown.analyze(
            equity, timestamps, bars_per_day
        )

        stat_tests = self.statistical_tests.run_all_tests(
            returns, benchmark_returns
        )

        risk_metrics = self._compute_risk_metrics(
            equity, returns, trades
        )

        summary = self._create_summary(
            equity_analysis, drawdown_analysis, trade_analysis, risk_metrics
        )

        return PerformanceReport(
            summary=summary,
            equity_analysis=equity_analysis,
            drawdown_analysis=drawdown_analysis,
            trade_analysis=trade_analysis,
            returns_breakdown=returns_analysis,
            statistical_tests=stat_tests,
            risk_metrics=risk_metrics,
            metadata={
                "n_bars": len(equity),
                "n_trades": len(trades) if trades else 0,
                "risk_free_rate": self.risk_free_rate,
                "bars_per_day": bars_per_day,
            },
        )

    def _compute_risk_metrics(
        self,
        equity: np.ndarray,
        returns: np.ndarray,
        trades: Optional[List[TradeData]],
    ) -> Dict[str, float]:
        """Compute advanced risk metrics."""
        var_95 = float(np.percentile(returns, 5)) if len(returns) > 0 else 0.0
        var_99 = float(np.percentile(returns, 1)) if len(returns) > 0 else 0.0

        tail_returns = returns[returns <= var_95]
        cvar_95 = float(np.mean(tail_returns)) if len(tail_returns) > 0 else var_95

        tail_returns_99 = returns[returns <= var_99]
        cvar_99 = float(np.mean(tail_returns_99)) if len(tail_returns_99) > 0 else var_99

        n = len(returns)
        if n > 0:
            negative_returns = returns[returns < 0]
            ulcer_index = float(np.sqrt(np.mean(negative_returns ** 2))) if len(negative_returns) > 0 else 0.0
        else:
            ulcer_index = 0.0

        tail_ratio = abs(float(np.percentile(returns, 95)) / (float(np.percentile(returns, 5)) + 1e-10)) if len(returns) > 0 else 1.0

        kelly_fraction = 0.0
        if trades:
            wins = [t for t in trades if t.pnl > 0]
            losses = [t for t in trades if t.pnl <= 0]
            if wins and losses:
                win_rate = len(wins) / len(trades)
                avg_win = np.mean([t.pnl for t in wins])
                avg_loss = np.mean([abs(t.pnl) for t in losses])
                if avg_loss > 0:
                    kelly_fraction = float(
                        win_rate - (1 - win_rate) / (avg_win / avg_loss)
                    )

        return {
            "value_at_risk_95": var_95,
            "value_at_risk_99": var_99,
            "conditional_var_95": cvar_95,
            "conditional_var_99": cvar_99,
            "ulcer_index": ulcer_index,
            "tail_ratio": tail_ratio,
            "kelly_fraction": kelly_fraction,
            "half_kelly": kelly_fraction / 2,
        }

    @staticmethod
    def _create_summary(
        equity_analysis: Dict[str, Any],
        drawdown_analysis: Dict[str, Any],
        trade_analysis: Dict[str, Any],
        risk_metrics: Dict[str, float],
    ) -> Dict[str, float]:
        """Create a concise summary of key metrics."""
        summary: Dict[str, float] = {}

        for key in [
            "total_return_pct", "annualized_return", "sharpe_ratio",
            "sortino_ratio", "calmar_ratio", "volatility",
        ]:
            if key in equity_analysis:
                summary[key] = equity_analysis[key]

        for key in ["max_drawdown_pct", "avg_drawdown_pct"]:
            if key in drawdown_analysis:
                summary[key] = drawdown_analysis[key]

        for key in [
            "total_trades", "win_rate", "profit_factor",
            "expectancy", "avg_trade_pnl", "payoff_ratio",
        ]:
            if key in trade_analysis:
                summary[key] = trade_analysis[key]

        summary["value_at_risk_95"] = risk_metrics.get("value_at_risk_95", 0.0)
        summary["kelly_fraction"] = risk_metrics.get("kelly_fraction", 0.0)

        return summary

    def export_report(
        self,
        report: PerformanceReport,
        output_path: str,
    ) -> str:
        """Export the performance report to a JSON file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        serializable = {
            "summary": report.summary,
            "equity_analysis": self._make_serializable(report.equity_analysis),
            "drawdown_analysis": self._make_serializable(report.drawdown_analysis),
            "trade_analysis": self._make_serializable(report.trade_analysis),
            "returns_breakdown": self._make_serializable(report.returns_breakdown),
            "statistical_tests": self._make_serializable(report.statistical_tests),
            "risk_metrics": report.risk_metrics,
            "metadata": report.metadata,
        }

        with open(path, "w") as f:
            json.dump(serializable, f, indent=2, default=str)

        logger.info(f"Performance report exported to {path}")
        return str(path)

    def _make_serializable(self, obj: Any) -> Any:
        """Convert numpy types to Python native types for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return obj
