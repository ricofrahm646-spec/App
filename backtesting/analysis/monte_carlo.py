"""Monte Carlo simulation for trade-sequence analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class MonteCarloResult:
    """Stores the output of a Monte Carlo simulation run."""

    n_simulations: int
    original_equity_curve: np.ndarray
    simulated_final_equities: np.ndarray  # shape (n_simulations,)
    simulated_max_drawdowns: np.ndarray   # shape (n_simulations,)
    simulated_equity_curves: np.ndarray   # shape (n_simulations, n_trades+1)

    percentiles: Dict[str, Dict[str, float]] = field(default_factory=dict)
    probability_of_ruin: float = 0.0
    confidence_intervals: Dict[str, tuple] = field(default_factory=dict)

    # convenience --------------------------------------------------------
    @property
    def median_final_equity(self) -> float:
        return float(np.median(self.simulated_final_equities))

    @property
    def mean_final_equity(self) -> float:
        return float(np.mean(self.simulated_final_equities))

    @property
    def median_max_drawdown(self) -> float:
        return float(np.median(self.simulated_max_drawdowns))


class MonteCarlo:
    """Randomise trade order to assess strategy robustness.

    Parameters
    ----------
    initial_equity : float
        Starting account balance for each simulation.
    ruin_threshold : float
        Fraction of *initial_equity* at which the account is considered
        "ruined" (default 0.5 → 50 % loss).
    seed : int | None
        Reproducibility seed for the RNG.
    """

    def __init__(
        self,
        initial_equity: float = 10_000.0,
        ruin_threshold: float = 0.5,
        seed: Optional[int] = None,
    ) -> None:
        self.initial_equity = initial_equity
        self.ruin_threshold = ruin_threshold
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        trade_pnls: Sequence[float],
        n_simulations: int = 1_000,
        percentile_levels: Optional[List[float]] = None,
    ) -> MonteCarloResult:
        """Run *n_simulations* with randomly shuffled trade order.

        Parameters
        ----------
        trade_pnls : sequence of float
            Profit/loss of each historical trade (absolute, not percentage).
        n_simulations : int
            How many random permutations to evaluate.
        percentile_levels : list[float] | None
            Percentiles to report (default ``[5, 25, 50, 75, 95]``).
        """
        if percentile_levels is None:
            percentile_levels = [5.0, 25.0, 50.0, 75.0, 95.0]

        pnls = np.asarray(trade_pnls, dtype=np.float64)
        n_trades = len(pnls)
        if n_trades == 0:
            raise ValueError("trade_pnls must contain at least one trade")

        original_curve = self._build_equity_curve(pnls)

        sim_curves = np.empty((n_simulations, n_trades + 1), dtype=np.float64)
        sim_finals = np.empty(n_simulations, dtype=np.float64)
        sim_dds = np.empty(n_simulations, dtype=np.float64)

        ruin_count = 0
        ruin_level = self.initial_equity * self.ruin_threshold

        for i in range(n_simulations):
            shuffled = self._rng.permutation(pnls)
            curve = self._build_equity_curve(shuffled)
            sim_curves[i] = curve
            sim_finals[i] = curve[-1]
            sim_dds[i] = self._max_drawdown(curve)
            if np.min(curve) <= ruin_level:
                ruin_count += 1

        prob_ruin = ruin_count / n_simulations

        percentiles = self._compute_percentiles(
            sim_finals, sim_dds, percentile_levels
        )
        ci = self._confidence_intervals(sim_finals, sim_dds)

        return MonteCarloResult(
            n_simulations=n_simulations,
            original_equity_curve=original_curve,
            simulated_final_equities=sim_finals,
            simulated_max_drawdowns=sim_dds,
            simulated_equity_curves=sim_curves,
            percentiles=percentiles,
            probability_of_ruin=prob_ruin,
            confidence_intervals=ci,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_equity_curve(self, pnls: np.ndarray) -> np.ndarray:
        curve = np.empty(len(pnls) + 1, dtype=np.float64)
        curve[0] = self.initial_equity
        np.cumsum(pnls, out=curve[1:])
        curve[1:] += self.initial_equity
        return curve

    @staticmethod
    def _max_drawdown(equity_curve: np.ndarray) -> float:
        peak = np.maximum.accumulate(equity_curve)
        dd = (peak - equity_curve) / np.where(peak == 0, 1.0, peak)
        return float(np.max(dd))

    @staticmethod
    def _compute_percentiles(
        finals: np.ndarray,
        drawdowns: np.ndarray,
        levels: List[float],
    ) -> Dict[str, Dict[str, float]]:
        result: Dict[str, Dict[str, float]] = {}
        for lvl in levels:
            key = f"p{int(lvl)}"
            result[key] = {
                "final_equity": float(np.percentile(finals, lvl)),
                "max_drawdown": float(np.percentile(drawdowns, lvl)),
            }
        return result

    @staticmethod
    def _confidence_intervals(
        finals: np.ndarray, drawdowns: np.ndarray
    ) -> Dict[str, tuple]:
        return {
            "final_equity_95": (
                float(np.percentile(finals, 2.5)),
                float(np.percentile(finals, 97.5)),
            ),
            "final_equity_99": (
                float(np.percentile(finals, 0.5)),
                float(np.percentile(finals, 99.5)),
            ),
            "max_drawdown_95": (
                float(np.percentile(drawdowns, 2.5)),
                float(np.percentile(drawdowns, 97.5)),
            ),
        }
