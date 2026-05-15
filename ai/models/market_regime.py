"""
Market Regime Detection
========================

Identifies market regimes (trending, ranging, volatile) using Hidden Markov
Models, volatility clustering, and session-aware analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class RegimeType(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class RegimeState:
    """Current detected market regime with metadata."""

    regime: RegimeType
    confidence: float
    duration_bars: int
    volatility: float
    trend_strength: float
    session: str = "unknown"
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class SessionConfig:
    """Trading session time windows (UTC hours)."""

    name: str
    start_hour: int
    end_hour: int
    typical_volatility: float = 1.0


DEFAULT_SESSIONS = [
    SessionConfig("asian", 0, 8, typical_volatility=0.7),
    SessionConfig("london", 8, 16, typical_volatility=1.2),
    SessionConfig("new_york", 13, 21, typical_volatility=1.3),
    SessionConfig("overlap", 13, 16, typical_volatility=1.5),
]


class GaussianHMM:
    """
    Gaussian Hidden Markov Model for regime detection.

    Implements Baum-Welch (EM) for training and Viterbi for decoding,
    without requiring hmmlearn.
    """

    def __init__(self, n_states: int = 3, n_iterations: int = 100, tol: float = 1e-4):
        self.n_states = n_states
        self.n_iterations = n_iterations
        self.tol = tol
        self.transition_matrix: Optional[np.ndarray] = None
        self.initial_probs: Optional[np.ndarray] = None
        self.means: Optional[np.ndarray] = None
        self.variances: Optional[np.ndarray] = None
        self._fitted = False

    def fit(self, observations: np.ndarray) -> "GaussianHMM":
        """
        Fit HMM parameters using Baum-Welch (EM) algorithm.

        Args:
            observations: 1D array of observations or 2D (T, n_features).
        """
        if observations.ndim == 1:
            observations = observations.reshape(-1, 1)

        T, n_feat = observations.shape
        n = self.n_states

        self.initial_probs = np.ones(n) / n
        self.transition_matrix = np.ones((n, n)) / n

        indices = np.linspace(0, T - 1, n + 2, dtype=int)[1:-1]
        self.means = observations[indices].copy()

        overall_var = np.var(observations, axis=0)
        self.variances = np.tile(overall_var, (n, 1)) + 1e-6

        prev_log_likelihood = -np.inf

        for iteration in range(self.n_iterations):
            log_emission = self._log_emission_probs(observations)
            log_alpha = self._forward(log_emission)
            log_beta = self._backward(log_emission)

            log_likelihood = self._logsumexp(log_alpha[-1])

            if abs(log_likelihood - prev_log_likelihood) < self.tol:
                logger.info(f"HMM converged at iteration {iteration}")
                break
            prev_log_likelihood = log_likelihood

            log_gamma = log_alpha + log_beta
            log_gamma -= self._logsumexp(log_gamma, axis=1, keepdims=True)
            gamma = np.exp(log_gamma)

            log_xi = np.zeros((T - 1, n, n))
            log_trans = np.log(self.transition_matrix + 1e-300)
            for t in range(T - 1):
                for i in range(n):
                    for j in range(n):
                        log_xi[t, i, j] = (
                            log_alpha[t, i]
                            + log_trans[i, j]
                            + log_emission[t + 1, j]
                            + log_beta[t + 1, j]
                        )
                log_xi[t] -= self._logsumexp(log_xi[t].ravel())
            xi = np.exp(log_xi)

            self.initial_probs = gamma[0] + 1e-10
            self.initial_probs /= self.initial_probs.sum()

            for i in range(n):
                denom = gamma[:-1, i].sum() + 1e-10
                for j in range(n):
                    self.transition_matrix[i, j] = xi[:, i, j].sum() / denom

            for i in range(n):
                weight_sum = gamma[:, i].sum() + 1e-10
                self.means[i] = (gamma[:, i:i + 1] * observations).sum(axis=0) / weight_sum
                diff = observations - self.means[i]
                self.variances[i] = (
                    (gamma[:, i:i + 1] * diff ** 2).sum(axis=0) / weight_sum
                )
                self.variances[i] = np.maximum(self.variances[i], 1e-6)

        self._fitted = True
        return self

    def predict(self, observations: np.ndarray) -> np.ndarray:
        """Decode the most likely state sequence using the Viterbi algorithm."""
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if observations.ndim == 1:
            observations = observations.reshape(-1, 1)

        T = observations.shape[0]
        n = self.n_states
        log_emission = self._log_emission_probs(observations)
        log_trans = np.log(self.transition_matrix + 1e-300)

        viterbi = np.zeros((T, n))
        backpointer = np.zeros((T, n), dtype=int)

        viterbi[0] = np.log(self.initial_probs + 1e-300) + log_emission[0]

        for t in range(1, T):
            for j in range(n):
                scores = viterbi[t - 1] + log_trans[:, j]
                backpointer[t, j] = np.argmax(scores)
                viterbi[t, j] = scores[backpointer[t, j]] + log_emission[t, j]

        states = np.zeros(T, dtype=int)
        states[-1] = np.argmax(viterbi[-1])
        for t in range(T - 2, -1, -1):
            states[t] = backpointer[t + 1, states[t + 1]]

        return states

    def predict_proba(self, observations: np.ndarray) -> np.ndarray:
        """Return posterior state probabilities for each time step."""
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        if observations.ndim == 1:
            observations = observations.reshape(-1, 1)

        log_emission = self._log_emission_probs(observations)
        log_alpha = self._forward(log_emission)
        log_beta = self._backward(log_emission)

        log_gamma = log_alpha + log_beta
        log_gamma -= self._logsumexp(log_gamma, axis=1, keepdims=True)
        return np.exp(log_gamma)

    def _log_emission_probs(self, observations: np.ndarray) -> np.ndarray:
        T = observations.shape[0]
        n = self.n_states
        log_emission = np.zeros((T, n))
        for j in range(n):
            diff = observations - self.means[j]
            log_emission[:, j] = -0.5 * np.sum(
                np.log(2 * np.pi * self.variances[j]) + diff ** 2 / self.variances[j],
                axis=1,
            )
        return log_emission

    def _forward(self, log_emission: np.ndarray) -> np.ndarray:
        T, n = log_emission.shape
        log_alpha = np.full((T, n), -np.inf)
        log_alpha[0] = np.log(self.initial_probs + 1e-300) + log_emission[0]
        log_trans = np.log(self.transition_matrix + 1e-300)
        for t in range(1, T):
            for j in range(n):
                log_alpha[t, j] = (
                    self._logsumexp(log_alpha[t - 1] + log_trans[:, j])
                    + log_emission[t, j]
                )
        return log_alpha

    def _backward(self, log_emission: np.ndarray) -> np.ndarray:
        T, n = log_emission.shape
        log_beta = np.full((T, n), -np.inf)
        log_beta[-1] = 0.0
        log_trans = np.log(self.transition_matrix + 1e-300)
        for t in range(T - 2, -1, -1):
            for j in range(n):
                log_beta[t, j] = self._logsumexp(
                    log_trans[j, :] + log_emission[t + 1] + log_beta[t + 1]
                )
        return log_beta

    @staticmethod
    def _logsumexp(
        a: np.ndarray, axis: Optional[int] = None, keepdims: bool = False
    ) -> np.ndarray:
        a_max = np.max(a, axis=axis, keepdims=True)
        result = a_max + np.log(np.sum(np.exp(a - a_max), axis=axis, keepdims=True))
        if not keepdims:
            result = np.squeeze(result, axis=axis)
        return result


class VolatilityRegimeClusterer:
    """Cluster volatility into regimes using k-means on volatility features."""

    def __init__(self, n_clusters: int = 3, lookback: int = 20, seed: int = 42):
        self.n_clusters = n_clusters
        self.lookback = lookback
        self.seed = seed
        self.centroids: Optional[np.ndarray] = None
        self._regime_labels: Dict[int, RegimeType] = {}

    def fit(self, returns: np.ndarray) -> "VolatilityRegimeClusterer":
        """
        Fit volatility clusters on historical returns.

        Args:
            returns: Array of period returns.
        """
        features = self._extract_vol_features(returns)
        if features.shape[0] < self.n_clusters:
            raise ValueError("Not enough data points for clustering")

        self.centroids = self._kmeans(features)
        self._assign_regime_labels()
        return self

    def predict(self, returns: np.ndarray) -> np.ndarray:
        """Predict volatility regime for each period."""
        if self.centroids is None:
            raise RuntimeError("Model not fitted")
        features = self._extract_vol_features(returns)
        return self._assign_clusters(features)

    def predict_current(self, returns: np.ndarray) -> Tuple[RegimeType, float]:
        """Predict the current volatility regime and confidence."""
        if self.centroids is None:
            raise RuntimeError("Model not fitted")
        features = self._extract_vol_features(returns)
        if features.shape[0] == 0:
            return RegimeType.RANGING, 0.0

        last_features = features[-1:]
        distances = np.linalg.norm(self.centroids - last_features, axis=1)
        cluster = int(np.argmin(distances))
        min_dist = distances[cluster]
        total_dist = distances.sum()
        confidence = 1.0 - (min_dist / (total_dist + 1e-10))

        regime = self._regime_labels.get(cluster, RegimeType.RANGING)
        return regime, float(confidence)

    def _extract_vol_features(self, returns: np.ndarray) -> np.ndarray:
        n = len(returns)
        if n < self.lookback:
            return np.zeros((0, 4))

        features_list: List[np.ndarray] = []
        for i in range(self.lookback, n):
            window = returns[i - self.lookback: i]
            realized_vol = np.std(window)
            vol_of_vol = np.std(np.abs(window))
            skew = float(self._skewness(window))
            kurt = float(self._kurtosis(window))
            features_list.append([realized_vol, vol_of_vol, skew, kurt])

        features = np.array(features_list)
        mean = features.mean(axis=0)
        std = features.std(axis=0) + 1e-10
        return (features - mean) / std

    def _kmeans(self, data: np.ndarray, max_iter: int = 100) -> np.ndarray:
        rng = np.random.RandomState(self.seed)
        n = data.shape[0]
        indices = rng.choice(n, self.n_clusters, replace=False)
        centroids = data[indices].copy()

        for _ in range(max_iter):
            distances = np.linalg.norm(
                data[:, np.newaxis, :] - centroids[np.newaxis, :, :], axis=2
            )
            labels = np.argmin(distances, axis=1)
            new_centroids = np.zeros_like(centroids)
            for k in range(self.n_clusters):
                members = data[labels == k]
                if len(members) > 0:
                    new_centroids[k] = members.mean(axis=0)
                else:
                    new_centroids[k] = centroids[k]
            if np.allclose(centroids, new_centroids, atol=1e-6):
                break
            centroids = new_centroids

        return centroids

    def _assign_clusters(self, data: np.ndarray) -> np.ndarray:
        distances = np.linalg.norm(
            data[:, np.newaxis, :] - self.centroids[np.newaxis, :, :], axis=2
        )
        return np.argmin(distances, axis=1)

    def _assign_regime_labels(self) -> None:
        """Map cluster indices to regime types based on centroid volatility."""
        vol_idx = 0  # realized vol is the first feature
        sorted_indices = np.argsort(self.centroids[:, vol_idx])

        mapping = [RegimeType.LOW_VOLATILITY, RegimeType.RANGING, RegimeType.VOLATILE]
        for rank, cluster_idx in enumerate(sorted_indices):
            if rank < len(mapping):
                self._regime_labels[int(cluster_idx)] = mapping[rank]
            else:
                self._regime_labels[int(cluster_idx)] = RegimeType.VOLATILE

    @staticmethod
    def _skewness(arr: np.ndarray) -> float:
        n = len(arr)
        if n < 3:
            return 0.0
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((arr - mean) / std) ** 3))

    @staticmethod
    def _kurtosis(arr: np.ndarray) -> float:
        n = len(arr)
        if n < 4:
            return 0.0
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((arr - mean) / std) ** 4) - 3.0)


class SessionAnalyzer:
    """Analyze market behaviour within and across trading sessions."""

    def __init__(self, sessions: Optional[List[SessionConfig]] = None):
        self.sessions = sessions or DEFAULT_SESSIONS

    def get_current_session(self, hour_utc: int) -> SessionConfig:
        """Return the active trading session for a given UTC hour."""
        for session in self.sessions:
            if session.start_hour <= hour_utc < session.end_hour:
                return session
        return SessionConfig("off_hours", 21, 24, typical_volatility=0.5)

    def analyze_session_stats(
        self,
        returns: np.ndarray,
        hours: np.ndarray,
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute per-session statistics.

        Args:
            returns: Array of period returns.
            hours: Array of UTC hours for each return.

        Returns:
            Dict mapping session names to statistics.
        """
        results: Dict[str, Dict[str, float]] = {}

        for session in self.sessions:
            mask = (hours >= session.start_hour) & (hours < session.end_hour)
            session_returns = returns[mask]

            if len(session_returns) < 2:
                continue

            results[session.name] = {
                "mean_return": float(np.mean(session_returns)),
                "volatility": float(np.std(session_returns)),
                "sharpe": float(
                    np.mean(session_returns) / (np.std(session_returns) + 1e-10)
                    * np.sqrt(252)
                ),
                "skewness": float(VolatilityRegimeClusterer._skewness(session_returns)),
                "kurtosis": float(VolatilityRegimeClusterer._kurtosis(session_returns)),
                "num_observations": float(len(session_returns)),
                "positive_ratio": float(np.mean(session_returns > 0)),
            }

        return results

    def get_session_regime_bias(
        self,
        session_name: str,
        session_stats: Dict[str, Dict[str, float]],
    ) -> RegimeType:
        """Infer the dominant regime for a given session."""
        if session_name not in session_stats:
            return RegimeType.RANGING

        stats = session_stats[session_name]
        vol = stats["volatility"]
        mean_ret = stats["mean_return"]

        all_vols = [s["volatility"] for s in session_stats.values()]
        avg_vol = np.mean(all_vols) if all_vols else vol

        if vol > avg_vol * 1.5:
            return RegimeType.VOLATILE
        elif vol < avg_vol * 0.5:
            return RegimeType.LOW_VOLATILITY
        elif abs(mean_ret) > vol * 0.3:
            return RegimeType.TRENDING_UP if mean_ret > 0 else RegimeType.TRENDING_DOWN
        else:
            return RegimeType.RANGING


class MarketRegimeDetector:
    """
    Unified market regime detection combining HMM, volatility clustering,
    and session analysis.
    """

    def __init__(
        self,
        n_regimes: int = 3,
        vol_lookback: int = 20,
        trend_lookback: int = 50,
        sessions: Optional[List[SessionConfig]] = None,
    ):
        self.n_regimes = n_regimes
        self.vol_lookback = vol_lookback
        self.trend_lookback = trend_lookback
        self.hmm = GaussianHMM(n_states=n_regimes)
        self.vol_clusterer = VolatilityRegimeClusterer(
            n_clusters=n_regimes, lookback=vol_lookback
        )
        self.session_analyzer = SessionAnalyzer(sessions)
        self._fitted = False
        self._hmm_regime_map: Dict[int, RegimeType] = {}

    def fit(
        self,
        prices: np.ndarray,
        returns: Optional[np.ndarray] = None,
        hours: Optional[np.ndarray] = None,
    ) -> "MarketRegimeDetector":
        """
        Fit all regime detection models on historical data.

        Args:
            prices: Array of close prices.
            returns: Optional pre-computed returns (otherwise derived from prices).
            hours: Optional UTC hours for session analysis.
        """
        if returns is None:
            returns = np.diff(prices) / (prices[:-1] + 1e-10)

        hmm_features = self._prepare_hmm_features(prices, returns)
        self.hmm.fit(hmm_features)

        hmm_states = self.hmm.predict(hmm_features)
        self._map_hmm_states_to_regimes(hmm_states, returns, prices)

        try:
            self.vol_clusterer.fit(returns)
        except ValueError as e:
            logger.warning(f"Volatility clustering failed: {e}")

        if hours is not None:
            min_len = min(len(returns), len(hours))
            self._session_stats = self.session_analyzer.analyze_session_stats(
                returns[:min_len], hours[:min_len]
            )
        else:
            self._session_stats = {}

        self._fitted = True
        return self

    def detect(
        self,
        prices: np.ndarray,
        returns: Optional[np.ndarray] = None,
        current_hour: Optional[int] = None,
    ) -> RegimeState:
        """
        Detect the current market regime.

        Args:
            prices: Recent price array (at least vol_lookback bars).
            returns: Optional pre-computed returns.
            current_hour: Current UTC hour for session-aware detection.
        """
        if not self._fitted:
            raise RuntimeError("Detector not fitted. Call fit() first.")

        if returns is None:
            returns = np.diff(prices) / (prices[:-1] + 1e-10)

        hmm_features = self._prepare_hmm_features(prices, returns)
        hmm_states = self.hmm.predict(hmm_features)
        hmm_proba = self.hmm.predict_proba(hmm_features)

        current_hmm_state = int(hmm_states[-1])
        current_confidence = float(hmm_proba[-1, current_hmm_state])
        hmm_regime = self._hmm_regime_map.get(current_hmm_state, RegimeType.RANGING)

        try:
            vol_regime, vol_conf = self.vol_clusterer.predict_current(returns)
        except RuntimeError:
            vol_regime = RegimeType.RANGING
            vol_conf = 0.0

        regime, confidence = self._combine_regime_signals(
            hmm_regime, current_confidence,
            vol_regime, vol_conf,
            returns, prices,
        )

        duration = self._compute_regime_duration(hmm_states, current_hmm_state)
        volatility = float(np.std(returns[-self.vol_lookback:]))
        trend_strength = self._compute_trend_strength(prices)

        session_name = "unknown"
        if current_hour is not None:
            session = self.session_analyzer.get_current_session(current_hour)
            session_name = session.name

        return RegimeState(
            regime=regime,
            confidence=confidence,
            duration_bars=duration,
            volatility=volatility,
            trend_strength=trend_strength,
            session=session_name,
            features={
                "hmm_state": float(current_hmm_state),
                "hmm_confidence": current_confidence,
                "vol_regime_confidence": vol_conf,
                "recent_return": float(returns[-1]) if len(returns) > 0 else 0.0,
                "atr_ratio": float(volatility / (np.mean(np.abs(returns)) + 1e-10)),
            },
        )

    def detect_history(
        self,
        prices: np.ndarray,
        returns: Optional[np.ndarray] = None,
    ) -> List[RegimeType]:
        """Return regime classification for each bar in the history."""
        if not self._fitted:
            raise RuntimeError("Detector not fitted. Call fit() first.")

        if returns is None:
            returns = np.diff(prices) / (prices[:-1] + 1e-10)

        hmm_features = self._prepare_hmm_features(prices, returns)
        hmm_states = self.hmm.predict(hmm_features)

        regimes = [
            self._hmm_regime_map.get(int(s), RegimeType.RANGING)
            for s in hmm_states
        ]

        n_prices = len(prices)
        n_regimes = len(regimes)
        if n_regimes < n_prices:
            regimes = [regimes[0]] * (n_prices - n_regimes) + regimes

        return regimes

    def _prepare_hmm_features(
        self, prices: np.ndarray, returns: np.ndarray
    ) -> np.ndarray:
        n = len(returns)
        vol = np.zeros(n)
        for i in range(self.vol_lookback, n):
            vol[i] = np.std(returns[i - self.vol_lookback: i])
        vol[:self.vol_lookback] = vol[self.vol_lookback] if n > self.vol_lookback else 0

        mom = np.zeros(n)
        period = min(10, n)
        for i in range(period, n):
            mom[i] = np.mean(returns[i - period: i])

        return np.column_stack([returns, vol, mom])

    def _map_hmm_states_to_regimes(
        self,
        states: np.ndarray,
        returns: np.ndarray,
        prices: np.ndarray,
    ) -> None:
        """Map HMM state indices to RegimeType based on state characteristics."""
        state_stats: Dict[int, Dict[str, float]] = {}
        min_len = min(len(states), len(returns))

        for s in range(self.n_regimes):
            mask = states[:min_len] == s
            if mask.sum() == 0:
                state_stats[s] = {"mean_ret": 0.0, "vol": 0.0}
                continue
            s_returns = returns[:min_len][mask]
            state_stats[s] = {
                "mean_ret": float(np.mean(s_returns)),
                "vol": float(np.std(s_returns)),
            }

        sorted_by_vol = sorted(state_stats.items(), key=lambda x: x[1]["vol"])
        for rank, (state_idx, stats) in enumerate(sorted_by_vol):
            if rank == 0:
                if abs(stats["mean_ret"]) > stats["vol"] * 0.3:
                    self._hmm_regime_map[state_idx] = (
                        RegimeType.TRENDING_UP
                        if stats["mean_ret"] > 0
                        else RegimeType.TRENDING_DOWN
                    )
                else:
                    self._hmm_regime_map[state_idx] = RegimeType.LOW_VOLATILITY
            elif rank == len(sorted_by_vol) - 1:
                self._hmm_regime_map[state_idx] = RegimeType.VOLATILE
            else:
                if abs(stats["mean_ret"]) > stats["vol"] * 0.2:
                    self._hmm_regime_map[state_idx] = (
                        RegimeType.TRENDING_UP
                        if stats["mean_ret"] > 0
                        else RegimeType.TRENDING_DOWN
                    )
                else:
                    self._hmm_regime_map[state_idx] = RegimeType.RANGING

    def _combine_regime_signals(
        self,
        hmm_regime: RegimeType,
        hmm_conf: float,
        vol_regime: RegimeType,
        vol_conf: float,
        returns: np.ndarray,
        prices: np.ndarray,
    ) -> Tuple[RegimeType, float]:
        """Combine HMM and volatility clustering signals into a final regime."""
        trend_strength = self._compute_trend_strength(prices)
        recent_vol = float(np.std(returns[-self.vol_lookback:])) if len(returns) >= self.vol_lookback else 0.0
        full_vol = float(np.std(returns)) if len(returns) > 0 else 0.0

        if hmm_regime == vol_regime:
            return hmm_regime, (hmm_conf + vol_conf) / 2

        if recent_vol > full_vol * 2.0:
            return RegimeType.VOLATILE, max(hmm_conf, vol_conf)

        if trend_strength > 0.7:
            recent_ret = np.mean(returns[-self.vol_lookback:]) if len(returns) >= self.vol_lookback else 0.0
            direction = RegimeType.TRENDING_UP if recent_ret > 0 else RegimeType.TRENDING_DOWN
            return direction, trend_strength

        hmm_weight = 0.6
        vol_weight = 0.4
        if hmm_conf * hmm_weight >= vol_conf * vol_weight:
            return hmm_regime, hmm_conf
        else:
            return vol_regime, vol_conf

    def _compute_trend_strength(self, prices: np.ndarray) -> float:
        """ADX-inspired trend strength from 0 to 1."""
        lookback = min(self.trend_lookback, len(prices))
        if lookback < 5:
            return 0.0

        recent = prices[-lookback:]
        x = np.arange(lookback)
        x_mean = x.mean()
        y_mean = recent.mean()
        denom = np.sum((x - x_mean) ** 2)
        if denom == 0:
            return 0.0

        slope = np.sum((x - x_mean) * (recent - y_mean)) / denom
        y_pred = y_mean + slope * (x - x_mean)
        ss_res = np.sum((recent - y_pred) ** 2)
        ss_tot = np.sum((recent - y_mean) ** 2)

        if ss_tot == 0:
            return 0.0

        r_squared = 1.0 - ss_res / ss_tot
        return max(0.0, min(1.0, r_squared))

    @staticmethod
    def _compute_regime_duration(states: np.ndarray, current_state: int) -> int:
        """Count how many consecutive bars the current state has persisted."""
        duration = 0
        for i in range(len(states) - 1, -1, -1):
            if states[i] == current_state:
                duration += 1
            else:
                break
        return duration
