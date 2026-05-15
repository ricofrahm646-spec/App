"""
Monte Carlo Simulation
=======================

Trade sequence randomization, drawdown distribution analysis,
confidence intervals, risk of ruin calculation, and multi-path simulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation."""

    n_simulations: int = 10000
    initial_capital: float = 10000.0
    confidence_levels: List[float] = field(
        default_factory=lambda: [0.95, 0.99]
    )
    ruin_threshold: float = 0.5  # fraction of capital = ruin
    seed: int = 42
    method: str = "trade_shuffle"  # 'trade_shuffle', 'bootstrap', 'parametric'
    block_size: int = 5  # for block bootstrap


@dataclass
class SimulationPath:
    """A single Monte Carlo simulation path."""

    equity_curve: np.ndarray
    final_equity: float
    max_drawdown: float
    max_drawdown_duration: int
    total_return: float
    sharpe_ratio: float
    peak_equity: float
    is_ruined: bool


@dataclass
class MonteCarloResult:
    """Complete Monte Carlo simulation result."""

    n_simulations: int
    method: str

    mean_final_equity: float
    median_final_equity: float
    std_final_equity: float

    mean_max_drawdown: float
    median_max_drawdown: float
    worst_max_drawdown: float

    mean_return: float
    median_return: float

    risk_of_ruin: float

    confidence_intervals: Dict[float, Dict[str, float]]
    drawdown_distribution: Dict[str, float]
    return_distribution: Dict[str, float]

    paths_summary: Dict[str, float]
    percentiles: Dict[str, Dict[int, float]]

    config: MonteCarloConfig


class TradeShuffler:
    """Randomize trade sequences while preserving individual trade characteristics."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def shuffle(
        self, trade_pnls: np.ndarray, n_simulations: int
    ) -> np.ndarray:
        """
        Generate shuffled trade sequences.

        Args:
            trade_pnls: Original trade P&L array.
            n_simulations: Number of random permutations to generate.

        Returns:
            Array of shape (n_simulations, n_trades) with shuffled P&Ls.
        """
        n_trades = len(trade_pnls)
        simulated = np.zeros((n_simulations, n_trades))

        for i in range(n_simulations):
            simulated[i] = self.rng.permutation(trade_pnls)

        return simulated

    def block_shuffle(
        self, trade_pnls: np.ndarray, n_simulations: int, block_size: int = 5
    ) -> np.ndarray:
        """
        Block shuffle to preserve local autocorrelation.

        Trades are grouped into blocks and blocks are shuffled.
        """
        n_trades = len(trade_pnls)
        n_blocks = max(1, n_trades // block_size)
        simulated = np.zeros((n_simulations, n_trades))

        blocks = []
        for b in range(n_blocks):
            start = b * block_size
            end = min(start + block_size, n_trades)
            blocks.append(trade_pnls[start:end])

        for i in range(n_simulations):
            indices = self.rng.permutation(len(blocks))
            shuffled = np.concatenate([blocks[idx] for idx in indices])
            simulated[i, :len(shuffled)] = shuffled[:n_trades]

        return simulated


class BootstrapSampler:
    """Bootstrap sampling with replacement for trade P&Ls."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def sample(
        self, trade_pnls: np.ndarray, n_simulations: int,
        sample_size: Optional[int] = None,
    ) -> np.ndarray:
        """
        Bootstrap resample trade P&Ls.

        Args:
            trade_pnls: Original trade P&L array.
            n_simulations: Number of bootstrap samples.
            sample_size: Size of each sample (default = same as original).

        Returns:
            Array of shape (n_simulations, sample_size).
        """
        n_trades = len(trade_pnls)
        size = sample_size or n_trades
        simulated = np.zeros((n_simulations, size))

        for i in range(n_simulations):
            indices = self.rng.randint(0, n_trades, size=size)
            simulated[i] = trade_pnls[indices]

        return simulated


class ParametricSampler:
    """Parametric sampling assuming a distribution for trade P&Ls."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def sample(
        self, trade_pnls: np.ndarray, n_simulations: int,
        n_trades: Optional[int] = None,
    ) -> np.ndarray:
        """
        Generate trade P&Ls from a fitted distribution.

        Fits a skewed normal approximation to the empirical distribution.
        """
        size = n_trades or len(trade_pnls)
        mean = np.mean(trade_pnls)
        std = np.std(trade_pnls)
        skew = self._compute_skewness(trade_pnls)

        simulated = np.zeros((n_simulations, size))

        for i in range(n_simulations):
            base = self.rng.normal(mean, std, size=size)

            if abs(skew) > 0.1:
                u = self.rng.uniform(0, 1, size=size)
                skew_adjustment = np.sign(skew) * std * 0.3 * (u ** 2 - 0.5)
                base += skew_adjustment

            simulated[i] = base

        return simulated

    @staticmethod
    def _compute_skewness(arr: np.ndarray) -> float:
        n = len(arr)
        if n < 3:
            return 0.0
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((arr - mean) / std) ** 3))


class MonteCarloSimulator:
    """
    Run Monte Carlo simulations on trade results to assess strategy
    robustness and risk characteristics.
    """

    def __init__(self, config: Optional[MonteCarloConfig] = None):
        self.config = config or MonteCarloConfig()
        self.shuffler = TradeShuffler(seed=self.config.seed)
        self.bootstrapper = BootstrapSampler(seed=self.config.seed + 1)
        self.parametric = ParametricSampler(seed=self.config.seed + 2)

    def simulate(
        self,
        trade_pnls: np.ndarray,
        trade_returns: Optional[np.ndarray] = None,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation on trade P&Ls.

        Args:
            trade_pnls: Array of trade P&L values.
            trade_returns: Optional array of trade return percentages.

        Returns:
            MonteCarloResult with distributions and statistics.
        """
        trade_pnls = np.asarray(trade_pnls, dtype=np.float64)
        n_trades = len(trade_pnls)

        if n_trades < 3:
            logger.warning("Too few trades for meaningful Monte Carlo analysis")
            return self._minimal_result(trade_pnls)

        simulated_pnls = self._generate_simulations(trade_pnls)

        paths = self._compute_paths(simulated_pnls)

        return self._compile_results(paths)

    def simulate_equity_paths(
        self,
        trade_pnls: np.ndarray,
    ) -> np.ndarray:
        """
        Generate equity curve paths for visualization.

        Returns array of shape (n_simulations, n_trades + 1) with equity values.
        """
        simulated_pnls = self._generate_simulations(trade_pnls)
        initial = self.config.initial_capital

        equity_paths = np.zeros(
            (self.config.n_simulations, simulated_pnls.shape[1] + 1)
        )
        equity_paths[:, 0] = initial

        for i in range(simulated_pnls.shape[1]):
            equity_paths[:, i + 1] = equity_paths[:, i] + simulated_pnls[:, i]

        return equity_paths

    def risk_of_ruin(
        self,
        trade_pnls: np.ndarray,
        ruin_level: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate the probability of ruin at various levels.

        Args:
            trade_pnls: Trade P&L array.
            ruin_level: Fraction of initial capital (default from config).

        Returns:
            Dict with risk of ruin at different threshold levels.
        """
        ruin_level = ruin_level or self.config.ruin_threshold
        simulated_pnls = self._generate_simulations(trade_pnls)
        initial = self.config.initial_capital

        ruin_levels = [0.25, 0.50, 0.75, 0.90]
        results: Dict[str, float] = {}

        for level in ruin_levels:
            ruin_threshold = initial * (1 - level)
            n_ruined = 0

            for sim in range(self.config.n_simulations):
                equity = initial
                for pnl in simulated_pnls[sim]:
                    equity += pnl
                    if equity <= ruin_threshold:
                        n_ruined += 1
                        break

            results[f"ruin_{int(level * 100)}pct"] = n_ruined / self.config.n_simulations

        avg_trade = np.mean(trade_pnls)
        std_trade = np.std(trade_pnls)
        if std_trade > 0 and avg_trade > 0:
            z = avg_trade / std_trade
            analytical_ruin = np.exp(-2 * z * np.sqrt(len(trade_pnls)))
            results["analytical_estimate"] = float(min(analytical_ruin, 1.0))
        else:
            results["analytical_estimate"] = 1.0

        return results

    def drawdown_analysis(
        self, trade_pnls: np.ndarray
    ) -> Dict[str, Any]:
        """
        Analyze the distribution of maximum drawdowns across simulations.

        Returns detailed drawdown statistics and distribution percentiles.
        """
        simulated_pnls = self._generate_simulations(trade_pnls)
        initial = self.config.initial_capital

        max_drawdowns = np.zeros(self.config.n_simulations)
        max_dd_durations = np.zeros(self.config.n_simulations, dtype=int)

        for sim in range(self.config.n_simulations):
            equity = np.zeros(len(simulated_pnls[sim]) + 1)
            equity[0] = initial
            for j, pnl in enumerate(simulated_pnls[sim]):
                equity[j + 1] = equity[j] + pnl

            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / (peak + 1e-10)
            max_drawdowns[sim] = np.max(drawdown)

            dd_duration = 0
            max_dur = 0
            for j in range(1, len(equity)):
                if equity[j] < peak[j]:
                    dd_duration += 1
                    max_dur = max(max_dur, dd_duration)
                else:
                    dd_duration = 0
            max_dd_durations[sim] = max_dur

        percentiles = [5, 10, 25, 50, 75, 90, 95, 99]

        return {
            "mean_max_drawdown": float(np.mean(max_drawdowns)),
            "median_max_drawdown": float(np.median(max_drawdowns)),
            "std_max_drawdown": float(np.std(max_drawdowns)),
            "worst_max_drawdown": float(np.max(max_drawdowns)),
            "best_max_drawdown": float(np.min(max_drawdowns)),
            "mean_dd_duration": float(np.mean(max_dd_durations)),
            "max_dd_duration": int(np.max(max_dd_durations)),
            "percentiles": {
                p: float(np.percentile(max_drawdowns, p)) for p in percentiles
            },
            "duration_percentiles": {
                p: int(np.percentile(max_dd_durations, p)) for p in percentiles
            },
            "prob_dd_over_10pct": float(np.mean(max_drawdowns > 0.10)),
            "prob_dd_over_20pct": float(np.mean(max_drawdowns > 0.20)),
            "prob_dd_over_30pct": float(np.mean(max_drawdowns > 0.30)),
            "prob_dd_over_50pct": float(np.mean(max_drawdowns > 0.50)),
        }

    def _generate_simulations(self, trade_pnls: np.ndarray) -> np.ndarray:
        """Generate simulated trade sequences using the configured method."""
        if self.config.method == "trade_shuffle":
            return self.shuffler.shuffle(trade_pnls, self.config.n_simulations)
        elif self.config.method == "block_shuffle":
            return self.shuffler.block_shuffle(
                trade_pnls, self.config.n_simulations, self.config.block_size
            )
        elif self.config.method == "bootstrap":
            return self.bootstrapper.sample(trade_pnls, self.config.n_simulations)
        elif self.config.method == "parametric":
            return self.parametric.sample(trade_pnls, self.config.n_simulations)
        else:
            return self.shuffler.shuffle(trade_pnls, self.config.n_simulations)

    def _compute_paths(
        self, simulated_pnls: np.ndarray
    ) -> List[SimulationPath]:
        """Compute equity path statistics for each simulation."""
        initial = self.config.initial_capital
        ruin_capital = initial * (1 - self.config.ruin_threshold)
        paths: List[SimulationPath] = []

        for sim in range(self.config.n_simulations):
            n_trades = simulated_pnls.shape[1]
            equity = np.zeros(n_trades + 1)
            equity[0] = initial

            for j in range(n_trades):
                equity[j + 1] = equity[j] + simulated_pnls[sim, j]

            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / (peak + 1e-10)
            max_dd = float(np.max(drawdown))

            max_dd_dur = 0
            current_dur = 0
            for j in range(1, len(equity)):
                if equity[j] < peak[j]:
                    current_dur += 1
                    max_dd_dur = max(max_dd_dur, current_dur)
                else:
                    current_dur = 0

            final = equity[-1]
            total_return = (final - initial) / initial

            returns = np.diff(equity) / (equity[:-1] + 1e-10)
            sharpe = (
                float(np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252))
                if len(returns) > 1 else 0.0
            )

            is_ruined = float(np.min(equity)) <= ruin_capital

            paths.append(SimulationPath(
                equity_curve=equity,
                final_equity=final,
                max_drawdown=max_dd,
                max_drawdown_duration=max_dd_dur,
                total_return=total_return,
                sharpe_ratio=sharpe,
                peak_equity=float(np.max(equity)),
                is_ruined=is_ruined,
            ))

        return paths

    def _compile_results(self, paths: List[SimulationPath]) -> MonteCarloResult:
        """Compile simulation paths into aggregate statistics."""
        final_equities = np.array([p.final_equity for p in paths])
        max_drawdowns = np.array([p.max_drawdown for p in paths])
        total_returns = np.array([p.total_return for p in paths])
        sharpe_ratios = np.array([p.sharpe_ratio for p in paths])
        n_ruined = sum(1 for p in paths if p.is_ruined)

        confidence_intervals: Dict[float, Dict[str, float]] = {}
        for level in self.config.confidence_levels:
            alpha = (1 - level) / 2
            ci_lower = alpha * 100
            ci_upper = (1 - alpha) * 100
            confidence_intervals[level] = {
                "equity_lower": float(np.percentile(final_equities, ci_lower)),
                "equity_upper": float(np.percentile(final_equities, ci_upper)),
                "return_lower": float(np.percentile(total_returns, ci_lower)),
                "return_upper": float(np.percentile(total_returns, ci_upper)),
                "max_dd_lower": float(np.percentile(max_drawdowns, ci_lower)),
                "max_dd_upper": float(np.percentile(max_drawdowns, ci_upper)),
            }

        dd_percentiles = [5, 10, 25, 50, 75, 90, 95, 99]
        drawdown_distribution = {
            f"p{p}": float(np.percentile(max_drawdowns, p)) for p in dd_percentiles
        }
        drawdown_distribution.update({
            "mean": float(np.mean(max_drawdowns)),
            "std": float(np.std(max_drawdowns)),
        })

        return_distribution = {
            f"p{p}": float(np.percentile(total_returns, p)) for p in dd_percentiles
        }
        return_distribution.update({
            "mean": float(np.mean(total_returns)),
            "std": float(np.std(total_returns)),
        })

        percentile_keys = [5, 10, 25, 50, 75, 90, 95]
        percentiles = {
            "final_equity": {
                p: float(np.percentile(final_equities, p)) for p in percentile_keys
            },
            "max_drawdown": {
                p: float(np.percentile(max_drawdowns, p)) for p in percentile_keys
            },
            "total_return": {
                p: float(np.percentile(total_returns, p)) for p in percentile_keys
            },
            "sharpe_ratio": {
                p: float(np.percentile(sharpe_ratios, p)) for p in percentile_keys
            },
        }

        n_profitable = int(np.sum(total_returns > 0))
        paths_summary = {
            "n_profitable": float(n_profitable),
            "n_losing": float(len(paths) - n_profitable),
            "profitability_ratio": float(n_profitable / len(paths)),
            "mean_sharpe": float(np.mean(sharpe_ratios)),
            "median_sharpe": float(np.median(sharpe_ratios)),
            "positive_sharpe_ratio": float(np.mean(sharpe_ratios > 0)),
        }

        return MonteCarloResult(
            n_simulations=len(paths),
            method=self.config.method,
            mean_final_equity=float(np.mean(final_equities)),
            median_final_equity=float(np.median(final_equities)),
            std_final_equity=float(np.std(final_equities)),
            mean_max_drawdown=float(np.mean(max_drawdowns)),
            median_max_drawdown=float(np.median(max_drawdowns)),
            worst_max_drawdown=float(np.max(max_drawdowns)),
            mean_return=float(np.mean(total_returns)),
            median_return=float(np.median(total_returns)),
            risk_of_ruin=n_ruined / len(paths),
            confidence_intervals=confidence_intervals,
            drawdown_distribution=drawdown_distribution,
            return_distribution=return_distribution,
            paths_summary=paths_summary,
            percentiles=percentiles,
            config=self.config,
        )

    def _minimal_result(self, trade_pnls: np.ndarray) -> MonteCarloResult:
        """Generate a minimal result when there are too few trades."""
        total_pnl = float(np.sum(trade_pnls))
        final_equity = self.config.initial_capital + total_pnl
        total_return = total_pnl / self.config.initial_capital

        return MonteCarloResult(
            n_simulations=0,
            method=self.config.method,
            mean_final_equity=final_equity,
            median_final_equity=final_equity,
            std_final_equity=0.0,
            mean_max_drawdown=0.0,
            median_max_drawdown=0.0,
            worst_max_drawdown=0.0,
            mean_return=total_return,
            median_return=total_return,
            risk_of_ruin=0.0,
            confidence_intervals={},
            drawdown_distribution={},
            return_distribution={},
            paths_summary={"warning": "Too few trades for Monte Carlo analysis"},
            percentiles={},
            config=self.config,
        )
