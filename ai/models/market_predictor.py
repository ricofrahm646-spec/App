"""
Market Predictor - PyTorch LSTM Model for Market Prediction
============================================================

Provides a configurable LSTM-based neural network for predicting market
price direction probabilities from multi-timeframe feature inputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class MarketLSTMConfig:
    """Configuration for the MarketLSTM model."""

    input_size: int = 32
    hidden_size: int = 128
    num_layers: int = 3
    dropout: float = 0.2
    bidirectional: bool = False
    num_classes: int = 3  # up, down, neutral
    attention_heads: int = 4
    fc_hidden: int = 64
    sequence_length: int = 60
    timeframes: List[str] = field(
        default_factory=lambda: ["1m", "5m", "15m", "1h"]
    )


class FeatureNormalizer:
    """Online feature normalization using running statistics."""

    def __init__(self, num_features: int, momentum: float = 0.1, eps: float = 1e-8):
        self.num_features = num_features
        self.momentum = momentum
        self.eps = eps
        self.running_mean = np.zeros(num_features, dtype=np.float64)
        self.running_var = np.ones(num_features, dtype=np.float64)
        self._count = 0

    def partial_fit(self, x: np.ndarray) -> None:
        """Update running statistics with a new batch of data."""
        if x.ndim == 1:
            x = x.reshape(1, -1)
        batch_mean = np.mean(x, axis=0)
        batch_var = np.var(x, axis=0)
        batch_size = x.shape[0]

        if self._count == 0:
            self.running_mean = batch_mean
            self.running_var = batch_var
        else:
            self.running_mean = (
                (1 - self.momentum) * self.running_mean + self.momentum * batch_mean
            )
            self.running_var = (
                (1 - self.momentum) * self.running_var + self.momentum * batch_var
            )
        self._count += batch_size

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Normalize features using running statistics."""
        return (x - self.running_mean) / np.sqrt(self.running_var + self.eps)

    def fit_transform(self, x: np.ndarray) -> np.ndarray:
        """Update statistics and normalize in one step."""
        self.partial_fit(x)
        return self.transform(x)

    def state_dict(self) -> Dict[str, np.ndarray]:
        return {
            "running_mean": self.running_mean.copy(),
            "running_var": self.running_var.copy(),
            "count": np.array([self._count]),
        }

    def load_state_dict(self, state: Dict[str, np.ndarray]) -> None:
        self.running_mean = state["running_mean"]
        self.running_var = state["running_var"]
        self._count = int(state["count"][0])


class TemporalAttention(nn.Module):
    """Multi-head self-attention over temporal dimension."""

    def __init__(self, hidden_size: int, num_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        attn_out, attn_weights = self.attention(x, x, x)
        out = self.norm(x + attn_out)
        return out, attn_weights


class TimeframeEncoder(nn.Module):
    """Encodes features from a single timeframe using LSTM + attention."""

    def __init__(self, config: MarketLSTMConfig):
        super().__init__()
        num_directions = 2 if config.bidirectional else 1
        self.lstm = nn.LSTM(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            dropout=config.dropout if config.num_layers > 1 else 0.0,
            batch_first=True,
            bidirectional=config.bidirectional,
        )
        self.attention = TemporalAttention(
            hidden_size=config.hidden_size * num_directions,
            num_heads=config.attention_heads,
            dropout=config.dropout,
        )
        self.output_size = config.hidden_size * num_directions

    def forward(
        self, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        lstm_out, _ = self.lstm(x)
        attn_out, attn_weights = self.attention(lstm_out)
        pooled = attn_out.mean(dim=1)
        return pooled, attn_weights


class MarketLSTM(nn.Module):
    """
    Multi-timeframe LSTM model for market price direction prediction.

    Processes features from multiple timeframes through separate LSTM encoders,
    fuses them with attention, and outputs price direction probabilities.

    Args:
        config: Model configuration dataclass.
    """

    def __init__(self, config: Optional[MarketLSTMConfig] = None):
        super().__init__()
        self.config = config or MarketLSTMConfig()
        num_directions = 2 if self.config.bidirectional else 1
        encoder_output_size = self.config.hidden_size * num_directions

        self.timeframe_encoders = nn.ModuleDict(
            {
                tf: TimeframeEncoder(self.config)
                for tf in self.config.timeframes
            }
        )

        num_tf = len(self.config.timeframes)
        self.fusion_attention = nn.MultiheadAttention(
            embed_dim=encoder_output_size,
            num_heads=self.config.attention_heads,
            dropout=self.config.dropout,
            batch_first=True,
        )
        self.fusion_norm = nn.LayerNorm(encoder_output_size)

        self.classifier = nn.Sequential(
            nn.Linear(encoder_output_size, self.config.fc_hidden),
            nn.ReLU(),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.fc_hidden, self.config.fc_hidden // 2),
            nn.ReLU(),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.fc_hidden // 2, self.config.num_classes),
        )

        self.normalizer = FeatureNormalizer(self.config.input_size)
        self._init_weights()

    def _init_weights(self) -> None:
        for name, param in self.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param)
            elif "bias" in name and param.dim() == 1:
                nn.init.zeros_(param)

    def forward(
        self, features: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Forward pass through the multi-timeframe model.

        Args:
            features: Dict mapping timeframe names to tensors of shape
                      (batch_size, seq_len, input_size).

        Returns:
            logits: Tensor of shape (batch_size, num_classes).
            attention_weights: Dict of attention weight tensors per timeframe.
        """
        encoded = []
        all_attn_weights: Dict[str, torch.Tensor] = {}

        for tf_name, encoder in self.timeframe_encoders.items():
            if tf_name in features:
                tf_repr, attn_w = encoder(features[tf_name])
                encoded.append(tf_repr)
                all_attn_weights[tf_name] = attn_w

        if not encoded:
            raise ValueError(
                f"No matching timeframe data. Expected one of: {list(self.timeframe_encoders.keys())}"
            )

        stacked = torch.stack(encoded, dim=1)  # (batch, num_tf, hidden)
        fused, fusion_weights = self.fusion_attention(stacked, stacked, stacked)
        fused = self.fusion_norm(stacked + fused)
        all_attn_weights["fusion"] = fusion_weights

        pooled = fused.mean(dim=1)  # (batch, hidden)
        logits = self.classifier(pooled)
        return logits, all_attn_weights

    def predict(
        self, features: Dict[str, np.ndarray], normalize: bool = True
    ) -> Dict[str, np.ndarray]:
        """
        Predict price direction probabilities from raw features.

        Args:
            features: Dict mapping timeframe names to numpy arrays of shape
                      (seq_len, input_size) or (batch, seq_len, input_size).
            normalize: Whether to apply feature normalization.

        Returns:
            Dict with keys:
                - 'probabilities': Array of class probabilities (batch, num_classes).
                - 'predicted_class': Array of predicted class indices (batch,).
                - 'confidence': Array of prediction confidence scores (batch,).
                - 'direction': List of direction strings ('up', 'down', 'neutral').
        """
        self.eval()
        device = next(self.parameters()).device
        direction_labels = {0: "up", 1: "down", 2: "neutral"}

        tensor_features: Dict[str, torch.Tensor] = {}
        for tf_name, arr in features.items():
            if tf_name not in self.timeframe_encoders:
                continue
            arr = np.asarray(arr, dtype=np.float32)
            if arr.ndim == 2:
                arr = arr[np.newaxis, ...]  # add batch dim

            if normalize:
                batch, seq, feat = arr.shape
                flat = arr.reshape(-1, feat)
                flat = self.normalizer.transform(flat)
                arr = flat.reshape(batch, seq, feat)

            tensor_features[tf_name] = torch.tensor(arr, dtype=torch.float32).to(device)

        with torch.no_grad():
            logits, _ = self.forward(tensor_features)
            probs = F.softmax(logits, dim=-1).cpu().numpy()

        predicted = np.argmax(probs, axis=-1)
        confidence = np.max(probs, axis=-1)
        directions = [direction_labels.get(int(p), "neutral") for p in predicted]

        return {
            "probabilities": probs,
            "predicted_class": predicted,
            "confidence": confidence,
            "direction": directions,
        }

    def fit_normalizer(self, data: np.ndarray) -> None:
        """Fit the feature normalizer on training data."""
        if data.ndim == 3:
            data = data.reshape(-1, data.shape[-1])
        self.normalizer.partial_fit(data)

    def get_num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class MultiTimeframeFeatureExtractor:
    """Extracts and aligns features across multiple timeframes from OHLCV data."""

    TIMEFRAME_MINUTES = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "4h": 240, "1d": 1440,
    }

    def __init__(self, timeframes: List[str], feature_columns: Optional[List[str]] = None):
        self.timeframes = timeframes
        self.feature_columns = feature_columns

    def extract(
        self,
        ohlcv_data: Dict[str, np.ndarray],
        sequence_length: int = 60,
    ) -> Dict[str, np.ndarray]:
        """
        Extract multi-timeframe feature sequences from OHLCV data.

        Args:
            ohlcv_data: Dict mapping timeframe names to arrays with columns
                        [open, high, low, close, volume].
            sequence_length: Number of bars per sequence.

        Returns:
            Dict of feature arrays per timeframe, each of shape
            (num_sequences, sequence_length, num_features).
        """
        result: Dict[str, np.ndarray] = {}
        for tf in self.timeframes:
            if tf not in ohlcv_data:
                continue
            raw = np.asarray(ohlcv_data[tf], dtype=np.float64)
            features = self._compute_features(raw)
            sequences = self._create_sequences(features, sequence_length)
            if sequences is not None:
                result[tf] = sequences
        return result

    def _compute_features(self, ohlcv: np.ndarray) -> np.ndarray:
        """Compute technical features from OHLCV data."""
        if ohlcv.shape[1] < 5:
            raise ValueError("OHLCV data must have at least 5 columns")

        o, h, l, c, v = ohlcv[:, 0], ohlcv[:, 1], ohlcv[:, 2], ohlcv[:, 3], ohlcv[:, 4]
        n = len(c)

        returns = np.zeros(n)
        returns[1:] = np.diff(c) / (c[:-1] + 1e-10)

        log_returns = np.zeros(n)
        log_returns[1:] = np.diff(np.log(c + 1e-10))

        hl_range = (h - l) / (c + 1e-10)
        body_ratio = np.abs(c - o) / (h - l + 1e-10)
        upper_shadow = (h - np.maximum(o, c)) / (h - l + 1e-10)
        lower_shadow = (np.minimum(o, c) - l) / (h - l + 1e-10)

        vol_change = np.zeros(n)
        vol_change[1:] = np.diff(v) / (v[:-1] + 1e-10)

        sma_5 = self._rolling_mean(c, 5)
        sma_20 = self._rolling_mean(c, 20)
        sma_ratio = (c - sma_20) / (sma_20 + 1e-10)

        std_20 = self._rolling_std(c, 20)
        bb_upper = sma_20 + 2 * std_20
        bb_lower = sma_20 - 2 * std_20
        bb_width = (bb_upper - bb_lower) / (sma_20 + 1e-10)
        bb_position = (c - bb_lower) / (bb_upper - bb_lower + 1e-10)

        rsi = self._compute_rsi(c, 14)

        ema_12 = self._ema(c, 12)
        ema_26 = self._ema(c, 26)
        macd_line = ema_12 - ema_26
        macd_signal = self._ema(macd_line, 9)
        macd_hist = macd_line - macd_signal

        atr = self._compute_atr(h, l, c, 14)
        atr_ratio = atr / (c + 1e-10)

        vol_sma = self._rolling_mean(v, 20)
        vol_ratio = v / (vol_sma + 1e-10)

        volatility_5 = self._rolling_std(returns, 5)
        volatility_20 = self._rolling_std(returns, 20)

        momentum_5 = np.zeros(n)
        momentum_5[5:] = c[5:] / (c[:-5] + 1e-10) - 1
        momentum_10 = np.zeros(n)
        momentum_10[10:] = c[10:] / (c[:-10] + 1e-10) - 1

        high_20 = self._rolling_max(h, 20)
        low_20 = self._rolling_min(l, 20)
        donchian_pos = (c - low_20) / (high_20 - low_20 + 1e-10)

        obv = np.zeros(n)
        for i in range(1, n):
            if c[i] > c[i - 1]:
                obv[i] = obv[i - 1] + v[i]
            elif c[i] < c[i - 1]:
                obv[i] = obv[i - 1] - v[i]
            else:
                obv[i] = obv[i - 1]

        obv_norm = np.zeros(n)
        obv_max = self._rolling_max(np.abs(obv), 20)
        mask = obv_max > 0
        obv_norm[mask] = obv[mask] / obv_max[mask]

        hour_sin = np.zeros(n)
        hour_cos = np.zeros(n)

        features = np.column_stack([
            returns, log_returns, hl_range, body_ratio, upper_shadow,
            lower_shadow, vol_change, sma_ratio, bb_width, bb_position,
            rsi / 100.0, macd_hist / (c + 1e-10), atr_ratio, vol_ratio,
            volatility_5, volatility_20, momentum_5, momentum_10,
            donchian_pos, obv_norm, hour_sin, hour_cos,
            sma_5 / (c + 1e-10) - 1, ema_12 / (c + 1e-10) - 1,
            ema_26 / (c + 1e-10) - 1, macd_line / (c + 1e-10),
            macd_signal / (c + 1e-10), std_20 / (c + 1e-10),
            self._rolling_mean(returns, 5),
            self._rolling_mean(returns, 20),
            self._rolling_mean(vol_change, 5),
            self._rolling_mean(hl_range, 10),
        ])

        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        return features

    def _create_sequences(
        self, features: np.ndarray, seq_len: int
    ) -> Optional[np.ndarray]:
        n = features.shape[0]
        if n < seq_len:
            return None
        num_seqs = n - seq_len + 1
        sequences = np.zeros((num_seqs, seq_len, features.shape[1]), dtype=np.float32)
        for i in range(num_seqs):
            sequences[i] = features[i: i + seq_len]
        return sequences

    @staticmethod
    def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
        result = np.full_like(arr, np.nan)
        cumsum = np.cumsum(np.insert(arr, 0, 0))
        result[window - 1:] = (cumsum[window:] - cumsum[:-window]) / window
        result[:window - 1] = arr[:window - 1]
        return np.nan_to_num(result, nan=0.0)

    @staticmethod
    def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
        result = np.zeros_like(arr)
        for i in range(window - 1, len(arr)):
            result[i] = np.std(arr[i - window + 1: i + 1])
        return result

    @staticmethod
    def _rolling_max(arr: np.ndarray, window: int) -> np.ndarray:
        result = np.copy(arr)
        for i in range(window - 1, len(arr)):
            result[i] = np.max(arr[i - window + 1: i + 1])
        return result

    @staticmethod
    def _rolling_min(arr: np.ndarray, window: int) -> np.ndarray:
        result = np.copy(arr)
        for i in range(window - 1, len(arr)):
            result[i] = np.min(arr[i - window + 1: i + 1])
        return result

    @staticmethod
    def _ema(arr: np.ndarray, span: int) -> np.ndarray:
        alpha = 2.0 / (span + 1)
        result = np.zeros_like(arr)
        result[0] = arr[0]
        for i in range(1, len(arr)):
            result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
        return result

    @staticmethod
    def _compute_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        n = len(close)
        rsi = np.full(n, 50.0)
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        if len(gains) < period:
            return rsi

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
        return rsi

    @staticmethod
    def _compute_atr(
        high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> np.ndarray:
        n = len(close)
        tr = np.zeros(n)
        tr[0] = high[0] - low[0]
        for i in range(1, n):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
        atr = np.zeros(n)
        if n >= period:
            atr[period - 1] = np.mean(tr[:period])
            for i in range(period, n):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        return atr
