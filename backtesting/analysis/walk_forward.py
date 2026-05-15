"""Walk-forward analysis for strategy validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class WindowResult:
    """Performance for a single in-sample / out-of-sample window pair."""

    window_index: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    best_params: Dict[str, Any]
    is_return: float
    oos_return: float
    is_sharpe: float
    oos_sharpe: float
    is_max_drawdown: float
    oos_max_drawdown: float
    is_trades: int
    oos_trades: int


@dataclass
class WalkForwardResult:
    """Aggregate result of a full walk-forward analysis."""

    windows: List[WindowResult] = field(default_factory=list)

    @property
    def n_windows(self) -> int:
        return len(self.windows)

    @property
    def oos_returns(self) -> np.ndarray:
        return np.array([w.oos_return for w in self.windows])

    @property
    def is_returns(self) -> np.ndarray:
        return np.array([w.is_return for w in self.windows])

    @property
    def mean_oos_return(self) -> float:
        return float(np.mean(self.oos_returns)) if self.windows else 0.0

    @property
    def mean_is_return(self) -> float:
        return float(np.mean(self.is_returns)) if self.windows else 0.0

    @property
    def oos_win_rate(self) -> float:
        """Fraction of OOS windows that were profitable."""
        if not self.windows:
            return 0.0
        return float(np.mean(self.oos_returns > 0))

    @property
    def consistency_score(self) -> float:
        """Ratio of OOS mean return to IS mean return (1.0 = no overfit)."""
        if self.mean_is_return == 0:
            return 0.0
        return self.mean_oos_return / self.mean_is_return

    @property
    def overfitting_detected(self) -> bool:
        """Heuristic: overfit when OOS performance is < 30 % of IS."""
        return self.consistency_score < 0.30

    @property
    def robustness_index(self) -> float:
        """Fraction of windows where OOS return is > 0 *and* >= 25 % of IS."""
        if not self.windows:
            return 0.0
        robust = sum(
            1
            for w in self.windows
            if w.oos_return > 0
            and (w.is_return == 0 or w.oos_return / w.is_return >= 0.25)
        )
        return robust / len(self.windows)

    def summary(self) -> Dict[str, Any]:
        return {
            "n_windows": self.n_windows,
            "mean_is_return": self.mean_is_return,
            "mean_oos_return": self.mean_oos_return,
            "oos_win_rate": self.oos_win_rate,
            "consistency_score": self.consistency_score,
            "overfitting_detected": self.overfitting_detected,
            "robustness_index": self.robustness_index,
        }


# Type aliases for the callbacks the caller must supply.
OptimizeFunc = Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, Any]]
EvaluateFunc = Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, float]]


class WalkForwardAnalyzer:
    """Rolling walk-forward optimisation / validation.

    Parameters
    ----------
    is_ratio : float
        Fraction of each window used for in-sample optimisation (default 0.7).
    n_windows : int | None
        Number of rolling windows.  If *None* the window count is derived
        automatically from *step_size*.
    step_size : int | None
        Number of bars to step forward between successive windows. Ignored
        when *n_windows* is set explicitly.
    min_trades : int
        Minimum trade count per window to be considered valid.
    """

    def __init__(
        self,
        is_ratio: float = 0.70,
        n_windows: Optional[int] = None,
        step_size: Optional[int] = None,
        min_trades: int = 30,
    ) -> None:
        if not 0.0 < is_ratio < 1.0:
            raise ValueError("is_ratio must be in (0, 1)")
        self.is_ratio = is_ratio
        self.n_windows = n_windows
        self.step_size = step_size
        self.min_trades = min_trades

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(
        self,
        data: pd.DataFrame,
        optimize_fn: OptimizeFunc,
        evaluate_fn: EvaluateFunc,
        base_params: Optional[Dict[str, Any]] = None,
    ) -> WalkForwardResult:
        """Execute the walk-forward analysis.

        Parameters
        ----------
        data : pd.DataFrame
            Full historical dataset sorted by time (must have a
            ``DatetimeIndex`` or a ``datetime`` column).
        optimize_fn : callable(is_data, base_params) -> best_params
            Called on each in-sample slice.  Should return the best
            parameter dict found.
        evaluate_fn : callable(data_slice, params) -> metrics_dict
            Called on both IS and OOS slices with the chosen params.
            Must return a dict with at least ``"return"``, ``"sharpe"``,
            ``"max_drawdown"``, and ``"trades"`` keys.
        base_params : dict | None
            Starting parameter grid / defaults fed to *optimize_fn*.
        """
        if base_params is None:
            base_params = {}

        data = self._ensure_datetime_index(data)
        splits = self._generate_splits(data)
        result = WalkForwardResult()

        for idx, (is_slice, oos_slice) in enumerate(splits):
            best_params = optimize_fn(is_slice, base_params)
            is_metrics = evaluate_fn(is_slice, best_params)
            oos_metrics = evaluate_fn(oos_slice, best_params)

            window = WindowResult(
                window_index=idx,
                is_start=is_slice.index[0],
                is_end=is_slice.index[-1],
                oos_start=oos_slice.index[0],
                oos_end=oos_slice.index[-1],
                best_params=best_params,
                is_return=is_metrics.get("return", 0.0),
                oos_return=oos_metrics.get("return", 0.0),
                is_sharpe=is_metrics.get("sharpe", 0.0),
                oos_sharpe=oos_metrics.get("sharpe", 0.0),
                is_max_drawdown=is_metrics.get("max_drawdown", 0.0),
                oos_max_drawdown=oos_metrics.get("max_drawdown", 0.0),
                is_trades=int(is_metrics.get("trades", 0)),
                oos_trades=int(oos_metrics.get("trades", 0)),
            )
            result.windows.append(window)

        return result

    # ------------------------------------------------------------------
    # Splitting helpers
    # ------------------------------------------------------------------

    def _generate_splits(
        self, data: pd.DataFrame
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        n = len(data)
        if self.n_windows is not None:
            return self._splits_from_n_windows(data, n)
        return self._splits_from_step_size(data, n)

    def _splits_from_n_windows(
        self, data: pd.DataFrame, n: int
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        n_windows = max(self.n_windows or 1, 1)
        window_len = n // n_windows
        if window_len < 2:
            raise ValueError("Dataset too small for requested n_windows")

        splits: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
        for i in range(n_windows):
            start = i * window_len
            end = min(start + window_len, n)
            is_end = start + int((end - start) * self.is_ratio)
            if is_end <= start or is_end >= end:
                continue
            splits.append((data.iloc[start:is_end], data.iloc[is_end:end]))
        return splits

    def _splits_from_step_size(
        self, data: pd.DataFrame, n: int
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        step = self.step_size or max(n // 10, 1)
        window_len = int(step / (1 - self.is_ratio))
        splits: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
        start = 0
        while start + window_len <= n:
            is_end = start + int(window_len * self.is_ratio)
            oos_end = start + window_len
            if is_end <= start or is_end >= oos_end:
                break
            splits.append((data.iloc[start:is_end], data.iloc[is_end:oos_end]))
            start += step
        return splits

    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_datetime_index(data: pd.DataFrame) -> pd.DataFrame:
        if isinstance(data.index, pd.DatetimeIndex):
            return data
        if "datetime" in data.columns:
            data = data.set_index("datetime")
            return data
        if "date" in data.columns:
            data = data.set_index("date")
            return data
        return data
