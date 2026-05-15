"""
Walk-Forward Analysis
======================

Rolling window optimization with in-sample/out-of-sample splitting,
robustness scoring, and degradation detection for strategy validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """A single walk-forward optimization window."""

    window_id: int
    is_start: int
    is_end: int
    oos_start: int
    oos_end: int
    is_best_params: Dict[str, Any]
    is_score: float
    oos_score: float
    oos_trades: int
    degradation: float  # oos/is ratio
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class WalkForwardResult:
    """Complete walk-forward analysis result."""

    windows: List[WalkForwardWindow]
    aggregate_oos_score: float
    aggregate_is_score: float
    robustness_score: float
    degradation_score: float
    is_robust: bool
    summary: Dict[str, float]
    optimal_params: Dict[str, Any]


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward analysis."""

    n_windows: int = 8
    is_ratio: float = 0.7
    gap_bars: int = 0
    anchored: bool = False  # True = expanding window, False = rolling
    min_is_bars: int = 100
    min_oos_bars: int = 30
    min_trades_per_window: int = 10
    robustness_threshold: float = 0.6
    degradation_threshold: float = 0.5
    optimization_metric: str = "sharpe_ratio"


class WalkForwardOptimizer:
    """
    Walk-forward optimization engine that validates strategies by
    optimizing on in-sample data and testing on out-of-sample data
    across rolling windows.
    """

    def __init__(self, config: Optional[WalkForwardConfig] = None):
        self.config = config or WalkForwardConfig()

    def analyze(
        self,
        data_length: int,
        optimize_fn: Callable[[int, int], Tuple[Dict[str, Any], float]],
        evaluate_fn: Callable[[int, int, Dict[str, Any]], Dict[str, float]],
    ) -> WalkForwardResult:
        """
        Run walk-forward analysis.

        Args:
            data_length: Total number of bars in the dataset.
            optimize_fn: Function(start_idx, end_idx) -> (best_params, best_score)
                         that optimizes the strategy on the given data range.
            evaluate_fn: Function(start_idx, end_idx, params) -> metrics_dict
                         that evaluates a parameter set on the given data range.
                         Must return a dict containing the optimization_metric
                         and 'n_trades'.

        Returns:
            WalkForwardResult with per-window and aggregate statistics.
        """
        windows_config = self._create_windows(data_length)

        if not windows_config:
            logger.error("Could not create walk-forward windows")
            return self._empty_result()

        windows: List[WalkForwardWindow] = []

        for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_config):
            logger.info(
                f"Window {i + 1}/{len(windows_config)}: "
                f"IS [{is_start}:{is_end}] OOS [{oos_start}:{oos_end}]"
            )

            try:
                best_params, is_score = optimize_fn(is_start, is_end)
            except Exception as e:
                logger.error(f"Optimization failed for window {i}: {e}")
                continue

            try:
                oos_metrics = evaluate_fn(oos_start, oos_end, best_params)
            except Exception as e:
                logger.error(f"OOS evaluation failed for window {i}: {e}")
                continue

            oos_score = oos_metrics.get(self.config.optimization_metric, 0.0)
            oos_trades = int(oos_metrics.get("n_trades", 0))

            degradation = oos_score / (is_score + 1e-10) if is_score != 0 else 0.0

            window = WalkForwardWindow(
                window_id=i,
                is_start=is_start,
                is_end=is_end,
                oos_start=oos_start,
                oos_end=oos_end,
                is_best_params=best_params,
                is_score=is_score,
                oos_score=oos_score,
                oos_trades=oos_trades,
                degradation=degradation,
                metrics=oos_metrics,
            )
            windows.append(window)

        return self._compile_results(windows)

    def _create_windows(
        self, data_length: int
    ) -> List[Tuple[int, int, int, int]]:
        """Create the walk-forward window boundaries."""
        n = self.config.n_windows
        gap = self.config.gap_bars
        min_is = self.config.min_is_bars
        min_oos = self.config.min_oos_bars

        total_min = min_is + min_oos + gap
        if data_length < total_min:
            logger.warning(
                f"Data length {data_length} too short for minimum "
                f"window size {total_min}"
            )
            return []

        window_size = data_length // n
        if window_size < min_is + min_oos + gap:
            n = max(1, data_length // total_min)
            window_size = data_length // n

        windows: List[Tuple[int, int, int, int]] = []

        for i in range(n):
            if self.config.anchored:
                is_start = 0
            else:
                is_start = i * (data_length - window_size * (n - i)) // n
                is_start = max(0, i * window_size - int(window_size * (1 - self.config.is_ratio)))

            oos_end = min((i + 1) * window_size, data_length)
            total_window = oos_end - is_start
            is_end = is_start + int(total_window * self.config.is_ratio)
            oos_start = is_end + gap

            is_end = min(is_end, data_length)
            oos_start = min(oos_start, data_length)
            oos_end = min(oos_end, data_length)

            if is_end - is_start < min_is:
                continue
            if oos_end - oos_start < min_oos:
                continue

            windows.append((is_start, is_end, oos_start, oos_end))

        return windows

    def _compile_results(
        self, windows: List[WalkForwardWindow]
    ) -> WalkForwardResult:
        """Compile individual window results into aggregate statistics."""
        if not windows:
            return self._empty_result()

        is_scores = [w.is_score for w in windows]
        oos_scores = [w.oos_score for w in windows]
        degradations = [w.degradation for w in windows]
        oos_trades = [w.oos_trades for w in windows]

        aggregate_is = float(np.mean(is_scores))
        aggregate_oos = float(np.mean(oos_scores))

        avg_degradation = float(np.mean(degradations))

        n_positive_oos = sum(1 for s in oos_scores if s > 0)
        consistency_ratio = n_positive_oos / len(windows)

        sufficient_trades = sum(
            1 for t in oos_trades if t >= self.config.min_trades_per_window
        )
        trade_sufficiency = sufficient_trades / len(windows)

        stability = 1.0 - min(
            float(np.std(oos_scores) / (abs(np.mean(oos_scores)) + 1e-10)), 2.0
        ) / 2.0

        robustness_score = (
            0.4 * consistency_ratio
            + 0.3 * min(avg_degradation, 1.0)
            + 0.2 * trade_sufficiency
            + 0.1 * stability
        )
        robustness_score = float(np.clip(robustness_score, 0.0, 1.0))

        degradation_score = float(np.clip(1.0 - avg_degradation, 0.0, 1.0))

        is_robust = (
            robustness_score >= self.config.robustness_threshold
            and consistency_ratio >= 0.5
            and avg_degradation >= self.config.degradation_threshold
        )

        best_window = max(windows, key=lambda w: w.oos_score)
        optimal_params = best_window.is_best_params

        window_pnls = [w.metrics.get("total_pnl", w.oos_score) for w in windows]
        cumulative_oos = float(np.sum(window_pnls))

        summary = {
            "n_windows": len(windows),
            "aggregate_is_score": aggregate_is,
            "aggregate_oos_score": aggregate_oos,
            "avg_degradation_ratio": avg_degradation,
            "consistency_ratio": consistency_ratio,
            "robustness_score": robustness_score,
            "stability": stability,
            "trade_sufficiency": trade_sufficiency,
            "cumulative_oos_pnl": cumulative_oos,
            "best_is_score": float(np.max(is_scores)),
            "worst_oos_score": float(np.min(oos_scores)),
            "oos_score_std": float(np.std(oos_scores)),
            "total_oos_trades": sum(oos_trades),
        }

        return WalkForwardResult(
            windows=windows,
            aggregate_oos_score=aggregate_oos,
            aggregate_is_score=aggregate_is,
            robustness_score=robustness_score,
            degradation_score=degradation_score,
            is_robust=is_robust,
            summary=summary,
            optimal_params=optimal_params,
        )

    def _empty_result(self) -> WalkForwardResult:
        return WalkForwardResult(
            windows=[],
            aggregate_oos_score=0.0,
            aggregate_is_score=0.0,
            robustness_score=0.0,
            degradation_score=0.0,
            is_robust=False,
            summary={},
            optimal_params={},
        )


class DegradationDetector:
    """Detect strategy performance degradation over time."""

    def __init__(
        self,
        lookback_windows: int = 5,
        significance_threshold: float = 0.05,
    ):
        self.lookback_windows = lookback_windows
        self.significance_threshold = significance_threshold

    def detect(
        self, wf_result: WalkForwardResult
    ) -> Dict[str, Any]:
        """
        Analyze walk-forward results for degradation patterns.

        Returns a dict with degradation indicators, trend analysis,
        and recommendations.
        """
        if len(wf_result.windows) < 3:
            return {
                "degradation_detected": False,
                "message": "Not enough windows for degradation analysis",
            }

        oos_scores = [w.oos_score for w in wf_result.windows]
        degradations = [w.degradation for w in wf_result.windows]

        trend = self._compute_trend(oos_scores)
        degradation_trend = self._compute_trend(degradations)

        n = len(oos_scores)
        recent = oos_scores[-min(self.lookback_windows, n):]
        earlier = oos_scores[:n - len(recent)] if len(recent) < n else oos_scores[:1]

        recent_mean = float(np.mean(recent))
        earlier_mean = float(np.mean(earlier)) if earlier else recent_mean

        declining = trend["slope"] < 0 and abs(trend["slope"]) > self.significance_threshold

        degradation_detected = (
            declining
            or recent_mean < earlier_mean * 0.5
            or np.mean(degradations[-3:]) < 0.3
        )

        structural_break = self._detect_structural_break(oos_scores)

        recommendations = []
        if degradation_detected:
            recommendations.append("Consider retraining the model on recent data")
            if trend["slope"] < -0.1:
                recommendations.append("Strategy may be over-optimized; reduce parameters")
            if structural_break["detected"]:
                recommendations.append(
                    f"Structural break at window {structural_break['break_point']}; "
                    "market regime may have changed"
                )

        return {
            "degradation_detected": degradation_detected,
            "oos_trend_slope": trend["slope"],
            "oos_trend_r_squared": trend["r_squared"],
            "degradation_trend_slope": degradation_trend["slope"],
            "recent_mean_oos": recent_mean,
            "earlier_mean_oos": earlier_mean,
            "structural_break": structural_break,
            "recommendations": recommendations,
        }

    @staticmethod
    def _compute_trend(values: List[float]) -> Dict[str, float]:
        """Fit a linear trend to a sequence of values."""
        n = len(values)
        if n < 2:
            return {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0}

        x = np.arange(n, dtype=np.float64)
        y = np.array(values, dtype=np.float64)

        x_mean = x.mean()
        y_mean = y.mean()

        ss_xy = np.sum((x - x_mean) * (y - y_mean))
        ss_xx = np.sum((x - x_mean) ** 2)

        if ss_xx == 0:
            return {"slope": 0.0, "intercept": float(y_mean), "r_squared": 0.0}

        slope = float(ss_xy / ss_xx)
        intercept = float(y_mean - slope * x_mean)

        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = float(1.0 - ss_res / (ss_tot + 1e-10)) if ss_tot > 0 else 0.0

        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": max(0.0, r_squared),
        }

    @staticmethod
    def _detect_structural_break(
        values: List[float],
    ) -> Dict[str, Any]:
        """
        Detect structural breaks using the Chow test approximation.

        Tests each potential break point and returns the most significant one.
        """
        n = len(values)
        if n < 6:
            return {"detected": False}

        y = np.array(values, dtype=np.float64)
        best_f_stat = 0.0
        best_break = -1
        total_sse = np.sum((y - y.mean()) ** 2)

        for bp in range(3, n - 3):
            y1 = y[:bp]
            y2 = y[bp:]
            sse1 = np.sum((y1 - y1.mean()) ** 2)
            sse2 = np.sum((y2 - y2.mean()) ** 2)
            sse_combined = sse1 + sse2

            k = 2
            denominator = sse_combined / (n - 2 * k) if n > 2 * k else 1e-10
            if denominator > 0:
                f_stat = ((total_sse - sse_combined) / k) / denominator
            else:
                f_stat = 0.0

            if f_stat > best_f_stat:
                best_f_stat = f_stat
                best_break = bp

        threshold = 4.0  # approximate F-critical value
        detected = best_f_stat > threshold

        return {
            "detected": detected,
            "break_point": best_break,
            "f_statistic": float(best_f_stat),
            "threshold": threshold,
        }


class RobustnessAnalyzer:
    """Analyze strategy robustness across multiple dimensions."""

    def __init__(self):
        self.degradation_detector = DegradationDetector()

    def full_analysis(
        self,
        wf_result: WalkForwardResult,
    ) -> Dict[str, Any]:
        """
        Run comprehensive robustness analysis on walk-forward results.

        Returns a multi-dimensional robustness assessment.
        """
        degradation = self.degradation_detector.detect(wf_result)

        parameter_stability = self._assess_parameter_stability(wf_result)

        performance_consistency = self._assess_performance_consistency(wf_result)

        overall_score = (
            0.3 * wf_result.robustness_score
            + 0.25 * parameter_stability["score"]
            + 0.25 * performance_consistency["score"]
            + 0.2 * (1.0 - float(degradation.get("degradation_detected", False)))
        )

        grade = self._score_to_grade(overall_score)

        return {
            "overall_score": float(overall_score),
            "grade": grade,
            "walk_forward_robustness": wf_result.robustness_score,
            "degradation_analysis": degradation,
            "parameter_stability": parameter_stability,
            "performance_consistency": performance_consistency,
            "is_production_ready": overall_score >= 0.6 and not degradation.get("degradation_detected", True),
        }

    def _assess_parameter_stability(
        self, wf_result: WalkForwardResult
    ) -> Dict[str, Any]:
        """Check if optimal parameters are consistent across windows."""
        if len(wf_result.windows) < 2:
            return {"score": 0.5, "stable_params": [], "unstable_params": []}

        all_params: Dict[str, List[Any]] = {}
        for w in wf_result.windows:
            for key, value in w.is_best_params.items():
                all_params.setdefault(key, []).append(value)

        stable = []
        unstable = []

        for key, values in all_params.items():
            try:
                numeric_values = [float(v) for v in values]
                cv = np.std(numeric_values) / (abs(np.mean(numeric_values)) + 1e-10)
                if cv < 0.3:
                    stable.append(key)
                else:
                    unstable.append(key)
            except (ValueError, TypeError):
                from collections import Counter
                counter = Counter(str(v) for v in values)
                most_common_ratio = counter.most_common(1)[0][1] / len(values)
                if most_common_ratio >= 0.5:
                    stable.append(key)
                else:
                    unstable.append(key)

        total = len(stable) + len(unstable)
        score = len(stable) / total if total > 0 else 0.5

        return {
            "score": float(score),
            "stable_params": stable,
            "unstable_params": unstable,
        }

    def _assess_performance_consistency(
        self, wf_result: WalkForwardResult
    ) -> Dict[str, Any]:
        """Assess consistency of performance across windows."""
        if not wf_result.windows:
            return {"score": 0.0}

        oos_scores = [w.oos_score for w in wf_result.windows]
        n_positive = sum(1 for s in oos_scores if s > 0)
        consistency = n_positive / len(oos_scores)

        mean_score = np.mean(oos_scores)
        std_score = np.std(oos_scores)
        cv = std_score / (abs(mean_score) + 1e-10)

        stability = max(0.0, 1.0 - min(cv, 2.0) / 2.0)

        score = 0.5 * consistency + 0.5 * stability

        return {
            "score": float(score),
            "consistency_ratio": float(consistency),
            "stability": float(stability),
            "mean_oos": float(mean_score),
            "std_oos": float(std_score),
            "cv": float(cv),
        }

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 0.9:
            return "A+"
        elif score >= 0.8:
            return "A"
        elif score >= 0.7:
            return "B"
        elif score >= 0.6:
            return "C"
        elif score >= 0.5:
            return "D"
        return "F"
