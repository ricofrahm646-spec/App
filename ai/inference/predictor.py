"""
Inference Engine
=================

Real-time prediction pipeline with model loading, ensemble predictions,
confidence scoring, and live feature extraction.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ai.models.market_predictor import (
    FeatureNormalizer,
    MarketLSTM,
    MarketLSTMConfig,
    MultiTimeframeFeatureExtractor,
)
from ai.models.market_regime import MarketRegimeDetector, RegimeState, RegimeType

logger = logging.getLogger(__name__)


@dataclass
class PredictorConfig:
    """Inference engine configuration."""

    model_dir: str = "models"
    ensemble_method: str = "weighted_average"  # 'weighted_average', 'voting', 'stacking'
    confidence_threshold: float = 0.6
    min_models_agree: int = 2
    cache_predictions: bool = True
    cache_ttl_seconds: float = 60.0
    device: str = "auto"
    timeframes: List[str] = field(
        default_factory=lambda: ["1m", "5m", "15m", "1h"]
    )
    feature_lookback: int = 60


@dataclass
class Prediction:
    """Container for a single prediction result."""

    direction: str  # 'up', 'down', 'neutral'
    confidence: float
    probabilities: Dict[str, float]
    regime: Optional[str] = None
    model_predictions: Optional[Dict[str, Dict[str, Any]]] = None
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ModelRegistry:
    """Manage loading, versioning, and serving of trained models."""

    def __init__(self, model_dir: str, device: torch.device):
        self.model_dir = Path(model_dir)
        self.device = device
        self._models: Dict[str, nn.Module] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}
        self._model_weights: Dict[str, float] = {}
        self._normalizers: Dict[str, FeatureNormalizer] = {}

    def register_model(
        self,
        name: str,
        model: nn.Module,
        weight: float = 1.0,
        normalizer: Optional[FeatureNormalizer] = None,
    ) -> None:
        """Register a pre-loaded model for inference."""
        model = model.to(self.device)
        model.eval()
        self._models[name] = model
        self._model_weights[name] = weight
        if normalizer is not None:
            self._normalizers[name] = normalizer

    def load_model(
        self,
        name: str,
        checkpoint_path: str,
        config: Optional[MarketLSTMConfig] = None,
        weight: float = 1.0,
    ) -> nn.Module:
        """Load a model from a checkpoint file."""
        config = config or MarketLSTMConfig()
        model = MarketLSTM(config)

        checkpoint = torch.load(
            checkpoint_path, map_location=self.device, weights_only=False
        )
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)

        model = model.to(self.device)
        model.eval()

        self._models[name] = model
        self._model_weights[name] = weight
        self._model_configs[name] = {
            "checkpoint_path": checkpoint_path,
            "config": config,
        }

        if hasattr(model, "normalizer"):
            self._normalizers[name] = model.normalizer

        logger.info(f"Loaded model '{name}' from {checkpoint_path}")
        return model

    def load_all_from_directory(self, pattern: str = "*.pt") -> int:
        """Load all models matching the pattern from model_dir."""
        count = 0
        if not self.model_dir.exists():
            logger.warning(f"Model directory {self.model_dir} does not exist")
            return 0

        for path in sorted(self.model_dir.glob(pattern)):
            name = path.stem
            try:
                self.load_model(name, str(path))
                count += 1
            except Exception as e:
                logger.error(f"Failed to load model {name}: {e}")
        return count

    def get_model(self, name: str) -> nn.Module:
        if name not in self._models:
            raise KeyError(f"Model '{name}' not registered")
        return self._models[name]

    def get_all_models(self) -> Dict[str, nn.Module]:
        return dict(self._models)

    def get_weight(self, name: str) -> float:
        return self._model_weights.get(name, 1.0)

    @property
    def model_names(self) -> List[str]:
        return list(self._models.keys())

    @property
    def num_models(self) -> int:
        return len(self._models)


class PredictionCache:
    """TTL-based cache for predictions to avoid redundant computation."""

    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[float, Prediction]] = {}

    def get(self, key: str) -> Optional[Prediction]:
        if key in self._cache:
            timestamp, prediction = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return prediction
            del self._cache[key]
        return None

    def put(self, key: str, prediction: Prediction) -> None:
        self._cache[key] = (time.time(), prediction)

    def invalidate(self, key: Optional[str] = None) -> None:
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def cleanup(self) -> int:
        now = time.time()
        expired = [k for k, (t, _) in self._cache.items() if now - t >= self.ttl]
        for k in expired:
            del self._cache[k]
        return len(expired)


class LiveFeatureExtractor:
    """Extract features from live/streaming market data."""

    def __init__(self, config: PredictorConfig):
        self.config = config
        self._extractor = MultiTimeframeFeatureExtractor(
            timeframes=config.timeframes
        )
        self._buffers: Dict[str, List[np.ndarray]] = {
            tf: [] for tf in config.timeframes
        }
        self._max_buffer = config.feature_lookback * 3

    def update(self, timeframe: str, ohlcv_bar: np.ndarray) -> None:
        """
        Append a new OHLCV bar for the given timeframe.

        Args:
            timeframe: Timeframe identifier (e.g., '1m').
            ohlcv_bar: Array of [open, high, low, close, volume].
        """
        if timeframe not in self._buffers:
            self._buffers[timeframe] = []

        self._buffers[timeframe].append(np.asarray(ohlcv_bar))
        if len(self._buffers[timeframe]) > self._max_buffer:
            self._buffers[timeframe] = self._buffers[timeframe][-self._max_buffer:]

    def get_features(self) -> Dict[str, np.ndarray]:
        """
        Extract latest features from all buffered timeframes.

        Returns:
            Dict mapping timeframe names to feature arrays suitable for model input.
        """
        ohlcv_data: Dict[str, np.ndarray] = {}
        for tf, bars in self._buffers.items():
            if len(bars) >= self.config.feature_lookback:
                ohlcv_data[tf] = np.array(bars)

        if not ohlcv_data:
            return {}

        result = self._extractor.extract(
            ohlcv_data, sequence_length=self.config.feature_lookback
        )

        final: Dict[str, np.ndarray] = {}
        for tf, sequences in result.items():
            if sequences is not None and len(sequences) > 0:
                final[tf] = sequences[-1]

        return final

    def get_prices(self, timeframe: Optional[str] = None) -> np.ndarray:
        """Get close prices from the buffer."""
        tf = timeframe or self.config.timeframes[0]
        bars = self._buffers.get(tf, [])
        if not bars:
            return np.array([])
        return np.array([bar[3] for bar in bars])

    def clear(self, timeframe: Optional[str] = None) -> None:
        if timeframe:
            self._buffers[timeframe] = []
        else:
            self._buffers = {tf: [] for tf in self.config.timeframes}


class ConfidenceScorer:
    """Compute prediction confidence from model outputs and ensemble agreement."""

    def __init__(
        self,
        entropy_weight: float = 0.3,
        agreement_weight: float = 0.4,
        margin_weight: float = 0.3,
    ):
        self.entropy_weight = entropy_weight
        self.agreement_weight = agreement_weight
        self.margin_weight = margin_weight

    def score(
        self,
        probabilities: np.ndarray,
        model_predictions: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """
        Compute a composite confidence score.

        Args:
            probabilities: Ensemble probability distribution.
            model_predictions: Optional list of individual model predictions.

        Returns:
            Confidence score between 0 and 1.
        """
        entropy_score = self._entropy_confidence(probabilities)

        margin_score = self._margin_confidence(probabilities)

        agreement_score = 1.0
        if model_predictions and len(model_predictions) > 1:
            agreement_score = self._agreement_confidence(model_predictions)

        confidence = (
            self.entropy_weight * entropy_score
            + self.agreement_weight * agreement_score
            + self.margin_weight * margin_score
        )

        return float(np.clip(confidence, 0.0, 1.0))

    @staticmethod
    def _entropy_confidence(probs: np.ndarray) -> float:
        """Lower entropy = higher confidence."""
        probs = np.clip(probs, 1e-10, 1.0)
        entropy = -np.sum(probs * np.log(probs))
        max_entropy = np.log(len(probs))
        if max_entropy == 0:
            return 1.0
        return float(1.0 - entropy / max_entropy)

    @staticmethod
    def _margin_confidence(probs: np.ndarray) -> float:
        """Larger margin between top-2 predictions = higher confidence."""
        sorted_probs = np.sort(probs)[::-1]
        if len(sorted_probs) < 2:
            return float(sorted_probs[0])
        return float(sorted_probs[0] - sorted_probs[1])

    @staticmethod
    def _agreement_confidence(predictions: List[Dict[str, Any]]) -> float:
        """Higher agreement among models = higher confidence."""
        directions = [p.get("direction", "neutral") for p in predictions]
        if not directions:
            return 0.0
        from collections import Counter
        counter = Counter(directions)
        most_common_count = counter.most_common(1)[0][1]
        return most_common_count / len(directions)


class Predictor:
    """
    Production inference engine combining multiple models, feature extraction,
    regime detection, and ensemble prediction.
    """

    def __init__(self, config: Optional[PredictorConfig] = None):
        self.config = config or PredictorConfig()
        self.device = self._resolve_device()
        self.registry = ModelRegistry(self.config.model_dir, self.device)
        self.feature_extractor = LiveFeatureExtractor(self.config)
        self.confidence_scorer = ConfidenceScorer()
        self.cache = PredictionCache(self.config.cache_ttl_seconds) if self.config.cache_predictions else None
        self.regime_detector: Optional[MarketRegimeDetector] = None

    def _resolve_device(self) -> torch.device:
        if self.config.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.config.device)

    def load_models(self, model_dir: Optional[str] = None) -> int:
        """Load all available models from the model directory."""
        if model_dir:
            self.registry.model_dir = Path(model_dir)
        return self.registry.load_all_from_directory()

    def set_regime_detector(self, detector: MarketRegimeDetector) -> None:
        self.regime_detector = detector

    def predict(
        self,
        features: Optional[Dict[str, np.ndarray]] = None,
        use_cache: bool = True,
    ) -> Prediction:
        """
        Generate an ensemble prediction from all loaded models.

        Args:
            features: Optional pre-extracted features. If None, uses the
                      live feature extractor buffer.
            use_cache: Whether to check the prediction cache.

        Returns:
            Prediction with direction, confidence, and metadata.
        """
        if features is None:
            features = self.feature_extractor.get_features()

        if not features:
            return Prediction(
                direction="neutral",
                confidence=0.0,
                probabilities={"up": 0.33, "down": 0.33, "neutral": 0.34},
                metadata={"error": "No features available"},
            )

        cache_key = self._make_cache_key(features)
        if use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        model_predictions = self._get_model_predictions(features)

        if not model_predictions:
            return Prediction(
                direction="neutral",
                confidence=0.0,
                probabilities={"up": 0.33, "down": 0.33, "neutral": 0.34},
                metadata={"error": "No models available"},
            )

        ensemble_probs = self._ensemble(model_predictions)
        direction_labels = {0: "up", 1: "down", 2: "neutral"}
        predicted_idx = int(np.argmax(ensemble_probs))
        direction = direction_labels.get(predicted_idx, "neutral")

        confidence = self.confidence_scorer.score(
            ensemble_probs, model_predictions
        )

        if confidence < self.config.confidence_threshold:
            direction = "neutral"

        regime_str = None
        if self.regime_detector is not None:
            try:
                prices = self.feature_extractor.get_prices()
                if len(prices) > 50:
                    regime_state = self.regime_detector.detect(prices)
                    regime_str = regime_state.regime.value
            except Exception as e:
                logger.warning(f"Regime detection failed: {e}")

        prediction = Prediction(
            direction=direction,
            confidence=confidence,
            probabilities={
                "up": float(ensemble_probs[0]),
                "down": float(ensemble_probs[1]),
                "neutral": float(ensemble_probs[2]) if len(ensemble_probs) > 2 else 0.0,
            },
            regime=regime_str,
            model_predictions={
                p.get("model_name", f"model_{i}"): p
                for i, p in enumerate(model_predictions)
            },
        )

        if self.cache:
            self.cache.put(cache_key, prediction)

        return prediction

    def predict_from_ohlcv(
        self,
        ohlcv_data: Dict[str, np.ndarray],
        sequence_length: Optional[int] = None,
    ) -> Prediction:
        """
        Predict directly from OHLCV data without incremental updates.

        Args:
            ohlcv_data: Dict mapping timeframes to OHLCV arrays (n_bars, 5).
            sequence_length: Override the default feature lookback.
        """
        seq_len = sequence_length or self.config.feature_lookback
        extractor = MultiTimeframeFeatureExtractor(self.config.timeframes)
        features = extractor.extract(ohlcv_data, sequence_length=seq_len)

        final: Dict[str, np.ndarray] = {}
        for tf, sequences in features.items():
            if sequences is not None and len(sequences) > 0:
                final[tf] = sequences[-1]

        return self.predict(final, use_cache=False)

    def update_market_data(self, timeframe: str, ohlcv_bar: np.ndarray) -> None:
        """Feed a new OHLCV bar to the live feature extractor."""
        self.feature_extractor.update(timeframe, ohlcv_bar)

    def _get_model_predictions(
        self, features: Dict[str, np.ndarray]
    ) -> List[Dict[str, Any]]:
        predictions: List[Dict[str, Any]] = []
        direction_labels = {0: "up", 1: "down", 2: "neutral"}

        for name, model in self.registry.get_all_models().items():
            try:
                if isinstance(model, MarketLSTM):
                    result = model.predict(features, normalize=True)
                    pred = {
                        "model_name": name,
                        "probabilities": result["probabilities"][0],
                        "predicted_class": int(result["predicted_class"][0]),
                        "direction": result["direction"][0],
                        "confidence": float(result["confidence"][0]),
                        "weight": self.registry.get_weight(name),
                    }
                else:
                    tensor_features = {}
                    for tf, arr in features.items():
                        t = torch.tensor(arr, dtype=torch.float32)
                        if t.dim() == 2:
                            t = t.unsqueeze(0)
                        tensor_features[tf] = t.to(self.device)

                    model.eval()
                    with torch.no_grad():
                        logits, _ = model(tensor_features)
                        probs = F.softmax(logits, dim=-1).cpu().numpy()[0]

                    pred_class = int(np.argmax(probs))
                    pred = {
                        "model_name": name,
                        "probabilities": probs,
                        "predicted_class": pred_class,
                        "direction": direction_labels.get(pred_class, "neutral"),
                        "confidence": float(np.max(probs)),
                        "weight": self.registry.get_weight(name),
                    }

                predictions.append(pred)
            except Exception as e:
                logger.error(f"Prediction failed for model '{name}': {e}")

        return predictions

    def _ensemble(self, predictions: List[Dict[str, Any]]) -> np.ndarray:
        if not predictions:
            return np.array([0.33, 0.33, 0.34])

        if self.config.ensemble_method == "weighted_average":
            return self._weighted_average_ensemble(predictions)
        elif self.config.ensemble_method == "voting":
            return self._voting_ensemble(predictions)
        else:
            return self._weighted_average_ensemble(predictions)

    @staticmethod
    def _weighted_average_ensemble(predictions: List[Dict[str, Any]]) -> np.ndarray:
        total_weight = sum(p.get("weight", 1.0) for p in predictions)
        if total_weight == 0:
            total_weight = 1.0

        n_classes = len(predictions[0]["probabilities"])
        ensemble_probs = np.zeros(n_classes)

        for pred in predictions:
            weight = pred.get("weight", 1.0) / total_weight
            probs = np.asarray(pred["probabilities"])
            ensemble_probs += weight * probs

        ensemble_probs /= ensemble_probs.sum() + 1e-10
        return ensemble_probs

    @staticmethod
    def _voting_ensemble(predictions: List[Dict[str, Any]]) -> np.ndarray:
        if not predictions:
            return np.array([0.33, 0.33, 0.34])

        n_classes = len(predictions[0]["probabilities"])
        votes = np.zeros(n_classes)
        for pred in predictions:
            pred_class = pred.get("predicted_class", 0)
            weight = pred.get("weight", 1.0)
            votes[pred_class] += weight

        total = votes.sum()
        if total > 0:
            votes /= total
        else:
            votes = np.ones(n_classes) / n_classes

        return votes

    @staticmethod
    def _make_cache_key(features: Dict[str, np.ndarray]) -> str:
        parts = []
        for tf in sorted(features.keys()):
            arr = features[tf]
            h = hash(arr.tobytes())
            parts.append(f"{tf}:{h}")
        return "|".join(parts)
