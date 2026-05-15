"""
JARVIS Strategy Evaluator.

Provides comprehensive strategy evaluation, comparison, ranking, and
overfitting detection for the AI Trading Operating System.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from strategies.implementations.base_strategy import BaseStrategy, PerformanceMetrics


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single strategy."""

    strategy_name: str
    metrics: PerformanceMetrics
    train_metrics: Optional[PerformanceMetrics] = None
    test_metrics: Optional[PerformanceMetrics] = None
    overfitting_score: float = 0.0
    composite_score: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def is_overfit(self) -> bool:
        """Strategy is considered overfit if score exceeds threshold."""
        return self.overfitting_score > 0.5


@dataclass
class ComparisonResult:
    """Result of comparing multiple strategies."""

    results: List[EvaluationResult]
    ranking: List[str]
    best_strategy: str
    comparison_table: pd.DataFrame


class StrategyEvaluator:
    """Evaluates, compares, and ranks trading strategies.

    Provides comprehensive performance evaluation including:
    - Sharpe ratio, Sortino ratio, max drawdown, profit factor
    - Win rate, expectancy, risk-adjusted returns
    - Overfitting detection via train/test split analysis
    - Multi-criteria composite scoring and ranking
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade: float = 0.01,
        train_ratio: float = 0.7,
        composite_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.train_ratio = train_ratio
        self.composite_weights = composite_weights or {
            "sharpe_ratio": 0.25,
            "sortino_ratio": 0.15,
            "profit_factor": 0.15,
            "win_rate": 0.10,
            "max_drawdown_pct": 0.15,
            "expectancy": 0.10,
            "overfitting_penalty": 0.10,
        }

    def evaluate_strategy(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        detect_overfit: bool = True,
    ) -> EvaluationResult:
        """Perform a full performance evaluation on a strategy.

        Runs a backtest on the full dataset, and optionally splits data
        into train/test sets for overfitting detection.

        Args:
            strategy: The strategy to evaluate.
            data: OHLCV DataFrame.
            detect_overfit: Whether to perform train/test overfitting analysis.

        Returns:
            EvaluationResult with metrics, overfitting score, and composite score.
        """
        full_metrics = strategy.backtest(data, self.initial_balance, self.risk_per_trade)

        result = EvaluationResult(
            strategy_name=strategy.name,
            metrics=full_metrics,
            parameters=strategy.get_parameters(),
        )

        if detect_overfit and len(data) > 100:
            result.train_metrics, result.test_metrics = self._train_test_eval(
                strategy, data
            )
            result.overfitting_score = self._calculate_overfitting_score(
                result.train_metrics, result.test_metrics
            )

        result.composite_score = self._calculate_composite_score(result)
        result.notes = self._generate_evaluation_notes(result)

        return result

    def compare_strategies(
        self,
        strategies: List[BaseStrategy],
        data: pd.DataFrame,
    ) -> ComparisonResult:
        """Evaluate and compare multiple strategies on the same dataset.

        Args:
            strategies: List of strategies to compare.
            data: OHLCV DataFrame.

        Returns:
            ComparisonResult with ranked strategies and comparison table.
        """
        results = [self.evaluate_strategy(s, data) for s in strategies]

        ranked = sorted(results, key=lambda r: r.composite_score, reverse=True)
        ranking = [r.strategy_name for r in ranked]

        table = self._build_comparison_table(ranked)

        return ComparisonResult(
            results=ranked,
            ranking=ranking,
            best_strategy=ranking[0] if ranking else "",
            comparison_table=table,
        )

    def rank_strategies(
        self, strategies: List[BaseStrategy], data: Optional[pd.DataFrame] = None
    ) -> List[Tuple[str, float]]:
        """Rank strategies by composite score.

        If data is provided, runs full evaluations. Otherwise, uses
        existing metrics from strategies that have been backtested.

        Args:
            strategies: List of strategies to rank.
            data: Optional OHLCV data for evaluation.

        Returns:
            List of (strategy_name, composite_score) tuples, sorted descending.
        """
        if data is not None:
            comparison = self.compare_strategies(strategies, data)
            return [(r.strategy_name, r.composite_score) for r in comparison.results]

        scores: List[Tuple[str, float]] = []
        for strategy in strategies:
            result = EvaluationResult(
                strategy_name=strategy.name,
                metrics=strategy.metrics,
                parameters=strategy.get_parameters(),
            )
            result.composite_score = self._calculate_composite_score(result)
            scores.append((strategy.name, result.composite_score))

        return sorted(scores, key=lambda x: x[1], reverse=True)

    def _train_test_eval(
        self, strategy: BaseStrategy, data: pd.DataFrame
    ) -> Tuple[PerformanceMetrics, PerformanceMetrics]:
        """Split data into train/test and evaluate on each portion."""
        split_idx = int(len(data) * self.train_ratio)
        train_data = data.iloc[:split_idx].copy()
        test_data = data.iloc[split_idx:].copy()

        train_metrics = strategy.backtest(
            train_data, self.initial_balance, self.risk_per_trade
        )

        test_metrics = strategy.backtest(
            test_data, self.initial_balance, self.risk_per_trade
        )

        return train_metrics, test_metrics

    def _calculate_overfitting_score(
        self,
        train_metrics: PerformanceMetrics,
        test_metrics: PerformanceMetrics,
    ) -> float:
        """Calculate overfitting score based on train/test performance divergence.

        Score ranges from 0 (no overfitting) to 1 (severely overfit).
        Compares multiple metrics between train and test sets.
        """
        scores: List[float] = []

        if train_metrics.total_trades == 0 or test_metrics.total_trades == 0:
            return 0.5

        wr_diff = abs(train_metrics.win_rate - test_metrics.win_rate)
        scores.append(min(wr_diff / 0.3, 1.0))

        if train_metrics.sharpe_ratio != 0:
            sharpe_ratio = test_metrics.sharpe_ratio / train_metrics.sharpe_ratio if train_metrics.sharpe_ratio != 0 else 0
            sharpe_degradation = max(0, 1.0 - sharpe_ratio)
            scores.append(min(sharpe_degradation, 1.0))
        else:
            scores.append(0.5)

        if train_metrics.profit_factor > 0 and train_metrics.profit_factor != float("inf"):
            pf_ratio = test_metrics.profit_factor / train_metrics.profit_factor if train_metrics.profit_factor != 0 else 0
            pf_degradation = max(0, 1.0 - pf_ratio)
            scores.append(min(pf_degradation, 1.0))
        else:
            scores.append(0.5)

        if train_metrics.expectancy != 0:
            exp_diff = abs(train_metrics.expectancy - test_metrics.expectancy) / abs(train_metrics.expectancy)
            scores.append(min(exp_diff, 1.0))
        else:
            scores.append(0.5)

        dd_diff = abs(train_metrics.max_drawdown_pct - test_metrics.max_drawdown_pct)
        scores.append(min(dd_diff / 20.0, 1.0))

        return float(np.mean(scores)) if scores else 0.5

    def _calculate_composite_score(self, result: EvaluationResult) -> float:
        """Calculate a composite score from multiple performance metrics.

        Normalizes each metric to a 0-1 scale and applies weights.
        Higher scores indicate better strategy performance.
        """
        m = result.metrics
        weights = self.composite_weights

        score = 0.0

        sharpe_norm = self._normalize_metric(m.sharpe_ratio, -1.0, 4.0)
        score += weights.get("sharpe_ratio", 0) * sharpe_norm

        sortino_norm = self._normalize_metric(m.sortino_ratio, -1.0, 6.0)
        score += weights.get("sortino_ratio", 0) * sortino_norm

        pf = min(m.profit_factor, 10.0) if m.profit_factor != float("inf") else 10.0
        pf_norm = self._normalize_metric(pf, 0.0, 5.0)
        score += weights.get("profit_factor", 0) * pf_norm

        wr_norm = m.win_rate
        score += weights.get("win_rate", 0) * wr_norm

        dd_norm = 1.0 - self._normalize_metric(m.max_drawdown_pct, 0.0, 50.0)
        score += weights.get("max_drawdown_pct", 0) * dd_norm

        avg_trade = m.total_pnl / m.total_trades if m.total_trades > 0 else 0.0
        exp_norm = self._normalize_metric(avg_trade, -100.0, 200.0)
        score += weights.get("expectancy", 0) * exp_norm

        overfit_penalty = 1.0 - result.overfitting_score
        score += weights.get("overfitting_penalty", 0) * overfit_penalty

        return round(float(np.clip(score, 0.0, 1.0)), 4)

    @staticmethod
    def _normalize_metric(value: float, min_val: float, max_val: float) -> float:
        """Normalize a metric value to 0-1 range."""
        if np.isnan(value) or np.isinf(value):
            return 0.5
        return float(np.clip((value - min_val) / (max_val - min_val), 0.0, 1.0))

    def _build_comparison_table(
        self, results: List[EvaluationResult]
    ) -> pd.DataFrame:
        """Build a DataFrame comparing all strategy metrics side by side."""
        rows: List[Dict[str, Any]] = []

        for r in results:
            m = r.metrics
            row = {
                "Strategy": r.strategy_name,
                "Total Trades": m.total_trades,
                "Win Rate": round(m.win_rate * 100, 1),
                "Profit Factor": round(m.profit_factor, 2) if m.profit_factor != float("inf") else "Inf",
                "Sharpe Ratio": round(m.sharpe_ratio, 2),
                "Sortino Ratio": round(m.sortino_ratio, 2),
                "Max Drawdown %": round(m.max_drawdown_pct, 2),
                "Total PnL": round(m.total_pnl, 2),
                "Avg Win": round(m.avg_win, 2),
                "Avg Loss": round(m.avg_loss, 2),
                "Expectancy": round(m.expectancy, 2),
                "Max Consec Wins": m.max_consecutive_wins,
                "Max Consec Losses": m.max_consecutive_losses,
                "Overfit Score": round(r.overfitting_score, 3),
                "Composite Score": round(r.composite_score, 4),
            }
            rows.append(row)

        return pd.DataFrame(rows).set_index("Strategy")

    @staticmethod
    def _generate_evaluation_notes(result: EvaluationResult) -> List[str]:
        """Generate human-readable evaluation notes and warnings."""
        notes: List[str] = []
        m = result.metrics

        if m.total_trades == 0:
            notes.append("WARNING: No trades generated. Strategy may be too restrictive.")
            return notes

        if m.total_trades < 30:
            notes.append(
                f"LOW SAMPLE: Only {m.total_trades} trades. "
                "Results may not be statistically significant (need 30+)."
            )

        if m.win_rate > 0.8:
            notes.append(
                f"HIGH WIN RATE ({m.win_rate*100:.0f}%): Verify this isn't due to "
                "tight TP / wide SL ratio."
            )
        elif m.win_rate < 0.3:
            notes.append(
                f"LOW WIN RATE ({m.win_rate*100:.0f}%): Acceptable only if "
                "avg_win >> avg_loss (trend following style)."
            )

        if m.sharpe_ratio > 3.0:
            notes.append(
                f"SUSPICIOUS SHARPE ({m.sharpe_ratio:.2f}): Unusually high. "
                "Possible look-ahead bias or curve fitting."
            )
        elif m.sharpe_ratio < 0:
            notes.append(
                f"NEGATIVE SHARPE ({m.sharpe_ratio:.2f}): Strategy loses money "
                "on a risk-adjusted basis."
            )

        if m.max_drawdown_pct > 30:
            notes.append(
                f"HIGH DRAWDOWN ({m.max_drawdown_pct:.1f}%): "
                "Consider reducing position size or adding risk filters."
            )

        pf = m.profit_factor
        if pf != float("inf") and pf < 1.0:
            notes.append(
                f"UNPROFITABLE (PF={pf:.2f}): Strategy loses more than it makes."
            )
        elif pf != float("inf") and pf > 5.0:
            notes.append(
                f"VERY HIGH PF ({pf:.2f}): May be overfit or have survivorship bias."
            )

        if result.overfitting_score > 0.5:
            notes.append(
                f"OVERFIT DETECTED (score={result.overfitting_score:.2f}): "
                "Significant performance degradation on out-of-sample data."
            )
        elif result.overfitting_score > 0.3:
            notes.append(
                f"MILD OVERFIT WARNING (score={result.overfitting_score:.2f}): "
                "Some performance divergence between train/test."
            )

        if m.max_consecutive_losses > 10:
            notes.append(
                f"LONG LOSING STREAK ({m.max_consecutive_losses}): "
                "May cause psychological pressure in live trading."
            )

        if m.avg_loss != 0 and m.avg_win / abs(m.avg_loss) < 0.5:
            notes.append(
                "POOR RISK/REWARD: Average win is less than half of average loss."
            )

        if not notes:
            notes.append("Strategy passed all basic checks.")

        return notes

    def walk_forward_analysis(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        n_folds: int = 5,
        train_pct: float = 0.7,
    ) -> Dict[str, Any]:
        """Perform walk-forward analysis to test robustness.

        Splits data into rolling train/test windows and evaluates
        performance consistency across all windows.

        Args:
            strategy: The strategy to analyze.
            data: OHLCV DataFrame.
            n_folds: Number of walk-forward folds.
            train_pct: Fraction of each fold used for training.

        Returns:
            Dict with fold results, consistency metrics, and overall assessment.
        """
        fold_size = len(data) // n_folds
        fold_results: List[Dict[str, float]] = []

        for i in range(n_folds):
            fold_start = i * fold_size
            fold_end = min((i + 1) * fold_size + int(fold_size * (1 - train_pct)), len(data))
            fold_data = data.iloc[fold_start:fold_end].copy()

            if len(fold_data) < 50:
                continue

            split = int(len(fold_data) * train_pct)
            test_data = fold_data.iloc[split:].copy()

            if len(test_data) < 20:
                continue

            metrics = strategy.backtest(test_data, self.initial_balance, self.risk_per_trade)

            fold_results.append({
                "fold": i + 1,
                "trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "sharpe": metrics.sharpe_ratio,
                "profit_factor": metrics.profit_factor if metrics.profit_factor != float("inf") else 10.0,
                "pnl": metrics.total_pnl,
                "max_dd_pct": metrics.max_drawdown_pct,
            })

        if not fold_results:
            return {
                "folds": [],
                "consistent": False,
                "avg_sharpe": 0.0,
                "sharpe_std": 0.0,
                "profitable_folds": 0,
                "total_folds": 0,
            }

        sharpes = [f["sharpe"] for f in fold_results]
        pnls = [f["pnl"] for f in fold_results]

        profitable_folds = sum(1 for p in pnls if p > 0)

        return {
            "folds": fold_results,
            "consistent": profitable_folds >= len(fold_results) * 0.6,
            "avg_sharpe": float(np.mean(sharpes)),
            "sharpe_std": float(np.std(sharpes)),
            "profitable_folds": profitable_folds,
            "total_folds": len(fold_results),
            "avg_win_rate": float(np.mean([f["win_rate"] for f in fold_results])),
            "avg_profit_factor": float(np.mean([f["profit_factor"] for f in fold_results])),
        }

    def monte_carlo_analysis(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        n_simulations: int = 1000,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """Run Monte Carlo simulation on trade results for robustness testing.

        Randomly reshuffles trade returns to estimate the distribution of
        possible outcomes and calculate confidence intervals.

        Args:
            strategy: Strategy with existing backtest results.
            data: OHLCV DataFrame for backtesting (if no prior results).
            n_simulations: Number of Monte Carlo iterations.
            confidence_level: Confidence level for intervals (e.g., 0.95).

        Returns:
            Dict with distribution statistics and confidence intervals.
        """
        if strategy.metrics.total_trades == 0:
            strategy.backtest(data, self.initial_balance, self.risk_per_trade)

        if strategy.metrics.total_trades == 0:
            return {"error": "No trades to simulate"}

        trade_returns = np.array([t.pnl for t in strategy.metrics.trade_history])
        n_trades = len(trade_returns)

        final_pnls = np.zeros(n_simulations)
        max_drawdowns = np.zeros(n_simulations)

        rng = np.random.default_rng(42)

        for sim in range(n_simulations):
            shuffled = rng.choice(trade_returns, size=n_trades, replace=True)
            cum_pnl = np.cumsum(shuffled)
            final_pnls[sim] = cum_pnl[-1]

            peak = np.maximum.accumulate(cum_pnl)
            drawdowns = peak - cum_pnl
            max_drawdowns[sim] = np.max(drawdowns)

        lower_pct = (1.0 - confidence_level) / 2.0 * 100
        upper_pct = (1.0 - (1.0 - confidence_level) / 2.0) * 100

        return {
            "n_simulations": n_simulations,
            "original_pnl": float(np.sum(trade_returns)),
            "mean_pnl": float(np.mean(final_pnls)),
            "median_pnl": float(np.median(final_pnls)),
            "std_pnl": float(np.std(final_pnls)),
            "pnl_ci_lower": float(np.percentile(final_pnls, lower_pct)),
            "pnl_ci_upper": float(np.percentile(final_pnls, upper_pct)),
            "prob_profit": float(np.mean(final_pnls > 0)),
            "worst_case_pnl": float(np.min(final_pnls)),
            "best_case_pnl": float(np.max(final_pnls)),
            "mean_max_drawdown": float(np.mean(max_drawdowns)),
            "worst_drawdown": float(np.max(max_drawdowns)),
            "dd_ci_upper": float(np.percentile(max_drawdowns, upper_pct)),
        }
