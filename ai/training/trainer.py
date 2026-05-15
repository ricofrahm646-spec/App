"""
Model Training Pipeline
========================

End-to-end training pipeline for market prediction models with
walk-forward splitting, early stopping, checkpointing, and metrics logging.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset

logger = logging.getLogger(__name__)


@dataclass
class TrainerConfig:
    """Training configuration."""

    epochs: int = 100
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    lr_scheduler: str = "cosine"  # 'cosine', 'step', 'plateau'
    lr_step_size: int = 30
    lr_gamma: float = 0.1
    patience: int = 15
    min_delta: float = 1e-4
    gradient_clip: float = 1.0
    checkpoint_dir: str = "checkpoints"
    log_dir: str = "training_logs"
    device: str = "auto"
    num_workers: int = 0
    pin_memory: bool = True
    mixed_precision: bool = False
    walk_forward_splits: int = 5
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    label_smoothing: float = 0.0


class MarketDataset(Dataset):
    """PyTorch dataset for market prediction training data."""

    def __init__(
        self,
        features: Dict[str, np.ndarray],
        labels: np.ndarray,
        timeframes: Optional[List[str]] = None,
    ):
        """
        Args:
            features: Dict mapping timeframe names to arrays of shape
                      (num_samples, seq_len, num_features).
            labels: Target labels array (num_samples,).
            timeframes: Specific timeframes to use. If None, use all.
        """
        self.timeframes = timeframes or list(features.keys())
        self.features = {
            tf: torch.tensor(features[tf], dtype=torch.float32)
            for tf in self.timeframes
            if tf in features
        }
        self.labels = torch.tensor(labels, dtype=torch.long)
        self._validate()

    def _validate(self) -> None:
        sizes = set()
        for tf, tensor in self.features.items():
            sizes.add(tensor.shape[0])
        sizes.add(self.labels.shape[0])
        if len(sizes) > 1:
            raise ValueError(
                f"Inconsistent sample counts across timeframes/labels: {sizes}"
            )

    def __len__(self) -> int:
        return self.labels.shape[0]

    def __getitem__(self, idx: int) -> Tuple[Dict[str, torch.Tensor], torch.Tensor]:
        features = {tf: tensor[idx] for tf, tensor in self.features.items()}
        return features, self.labels[idx]


class EarlyStopping:
    """Early stopping with patience and minimum delta."""

    def __init__(self, patience: int = 10, min_delta: float = 1e-4, mode: str = "min"):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score: Optional[float] = None
        self.should_stop = False

    def __call__(self, score: float) -> bool:
        if self.best_score is None:
            self.best_score = score
            return False

        improved = (
            score < self.best_score - self.min_delta
            if self.mode == "min"
            else score > self.best_score + self.min_delta
        )

        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
                return True
        return False


class MetricsLogger:
    """Log and store training metrics with persistence."""

    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history: Dict[str, List[float]] = {}
        self._start_time = time.time()

    def log(self, epoch: int, metrics: Dict[str, float]) -> None:
        for key, value in metrics.items():
            self.history.setdefault(key, []).append(value)

        elapsed = time.time() - self._start_time
        parts = [f"Epoch {epoch}"]
        for key, value in metrics.items():
            parts.append(f"{key}={value:.4f}")
        parts.append(f"[{elapsed:.1f}s]")
        logger.info(" | ".join(parts))

    def save(self, filename: str = "training_history.json") -> str:
        path = self.log_dir / filename
        with open(path, "w") as f:
            json.dump(self.history, f, indent=2)
        return str(path)

    def get_best_epoch(self, metric: str, mode: str = "min") -> int:
        values = self.history.get(metric, [])
        if not values:
            return 0
        if mode == "min":
            return int(np.argmin(values))
        return int(np.argmax(values))


class ModelCheckpointer:
    """Save and load model checkpoints with versioning."""

    def __init__(self, checkpoint_dir: str, max_checkpoints: int = 5):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self._saved: List[Tuple[str, float]] = []

    def save(
        self,
        model: nn.Module,
        optimizer: optim.Optimizer,
        epoch: int,
        metrics: Dict[str, float],
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics,
            "config": config or {},
            "timestamp": time.time(),
        }

        filename = f"checkpoint_epoch_{epoch:04d}.pt"
        path = self.checkpoint_dir / filename
        torch.save(checkpoint, path)

        val_loss = metrics.get("val_loss", float("inf"))
        self._saved.append((str(path), val_loss))
        self._cleanup()

        logger.info(f"Saved checkpoint: {path}")
        return str(path)

    def save_best(
        self,
        model: nn.Module,
        optimizer: optim.Optimizer,
        epoch: int,
        metrics: Dict[str, float],
    ) -> str:
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics,
            "timestamp": time.time(),
        }
        path = self.checkpoint_dir / "best_model.pt"
        torch.save(checkpoint, path)
        return str(path)

    def load(
        self, path: str, model: nn.Module, optimizer: Optional[optim.Optimizer] = None
    ) -> Dict[str, Any]:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        if optimizer is not None and "optimizer_state_dict" in checkpoint:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        return checkpoint

    def load_best(
        self, model: nn.Module, optimizer: Optional[optim.Optimizer] = None
    ) -> Dict[str, Any]:
        path = self.checkpoint_dir / "best_model.pt"
        return self.load(str(path), model, optimizer)

    def _cleanup(self) -> None:
        self._saved.sort(key=lambda x: x[1])
        while len(self._saved) > self.max_checkpoints:
            worst_path, _ = self._saved.pop()
            best_path = str(self.checkpoint_dir / "best_model.pt")
            if os.path.exists(worst_path) and worst_path != best_path:
                os.remove(worst_path)


class WalkForwardSplitter:
    """Walk-forward train/validation/test splitting."""

    def __init__(
        self,
        n_splits: int = 5,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        gap: int = 0,
    ):
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.gap = gap

    def split(
        self, n_samples: int
    ) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        Generate walk-forward splits.

        Returns list of (train_indices, val_indices, test_indices) tuples.
        """
        splits: List[Tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        min_window = max(50, n_samples // (self.n_splits + 2))

        step_size = (n_samples - min_window) // self.n_splits
        if step_size < 1:
            step_size = 1

        for i in range(self.n_splits):
            end = min_window + (i + 1) * step_size
            end = min(end, n_samples)

            window = end
            train_end = int(window * self.train_ratio)
            val_end = train_end + self.gap + int(window * self.val_ratio)
            val_end = min(val_end, end)

            train_idx = np.arange(0, train_end)
            val_start = train_end + self.gap
            val_idx = np.arange(val_start, min(val_end, end))
            test_idx = np.arange(val_end, end)

            if len(train_idx) > 0 and len(val_idx) > 0:
                splits.append((train_idx, val_idx, test_idx))

        return splits


class FeatureEngineer:
    """Pre-process and engineer features for model training."""

    def __init__(self, clip_quantile: float = 0.99):
        self.clip_quantile = clip_quantile
        self._feature_stats: Dict[str, Dict[str, float]] = {}

    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        """Fit on training data and transform."""
        features = self._clip_outliers(features)
        features = self._normalize(features, fit=True)
        return features

    def transform(self, features: np.ndarray) -> np.ndarray:
        """Transform using previously fitted statistics."""
        features = self._clip_outliers(features)
        features = self._normalize(features, fit=False)
        return features

    def _clip_outliers(self, features: np.ndarray) -> np.ndarray:
        result = features.copy()
        if result.ndim == 2:
            for i in range(result.shape[1]):
                q_low = np.quantile(result[:, i], 1 - self.clip_quantile)
                q_high = np.quantile(result[:, i], self.clip_quantile)
                result[:, i] = np.clip(result[:, i], q_low, q_high)
        elif result.ndim == 3:
            for i in range(result.shape[2]):
                flat = result[:, :, i].ravel()
                q_low = np.quantile(flat, 1 - self.clip_quantile)
                q_high = np.quantile(flat, self.clip_quantile)
                result[:, :, i] = np.clip(result[:, :, i], q_low, q_high)
        return result

    def _normalize(self, features: np.ndarray, fit: bool = True) -> np.ndarray:
        result = features.copy()
        if result.ndim == 3:
            batch, seq, n_feat = result.shape
            flat = result.reshape(-1, n_feat)
        elif result.ndim == 2:
            flat = result
            n_feat = result.shape[1]
        else:
            return result

        for i in range(flat.shape[1]):
            col = flat[:, i]
            if fit:
                mean = float(np.mean(col))
                std = float(np.std(col))
                self._feature_stats[f"feat_{i}"] = {"mean": mean, "std": std}
            else:
                stats = self._feature_stats.get(f"feat_{i}", {"mean": 0.0, "std": 1.0})
                mean = stats["mean"]
                std = stats["std"]

            if std < 1e-10:
                flat[:, i] = 0.0
            else:
                flat[:, i] = (col - mean) / std

        if result.ndim == 3:
            return flat.reshape(batch, seq, n_feat)
        return flat

    def create_labels(
        self,
        prices: np.ndarray,
        horizon: int = 1,
        threshold: float = 0.0005,
    ) -> np.ndarray:
        """
        Create classification labels from price data.

        Args:
            prices: Close prices.
            horizon: Forward-looking period for returns.
            threshold: Minimum return for up/down classification.

        Returns:
            Labels: 0=up, 1=down, 2=neutral
        """
        n = len(prices)
        labels = np.full(n, 2, dtype=np.int64)  # default neutral

        for i in range(n - horizon):
            fwd_return = (prices[i + horizon] - prices[i]) / (prices[i] + 1e-10)
            if fwd_return > threshold:
                labels[i] = 0  # up
            elif fwd_return < -threshold:
                labels[i] = 1  # down

        return labels


def _collate_dict_batch(
    batch: List[Tuple[Dict[str, torch.Tensor], torch.Tensor]]
) -> Tuple[Dict[str, torch.Tensor], torch.Tensor]:
    """Custom collate function for dict-based feature batches."""
    features_list, labels_list = zip(*batch)
    keys = features_list[0].keys()
    collated_features = {
        key: torch.stack([f[key] for f in features_list]) for key in keys
    }
    collated_labels = torch.stack(labels_list)
    return collated_features, collated_labels


class Trainer:
    """
    Complete model training pipeline with walk-forward validation,
    early stopping, checkpointing, and logging.
    """

    def __init__(self, config: Optional[TrainerConfig] = None):
        self.config = config or TrainerConfig()
        self.device = self._resolve_device()
        self.metrics_logger = MetricsLogger(self.config.log_dir)
        self.checkpointer = ModelCheckpointer(self.config.checkpoint_dir)
        self.feature_engineer = FeatureEngineer()

    def _resolve_device(self) -> torch.device:
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            return torch.device("cpu")
        return torch.device(self.config.device)

    def train(
        self,
        model: nn.Module,
        dataset: MarketDataset,
        class_weights: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Train the model on the dataset with walk-forward validation.

        Args:
            model: PyTorch model to train.
            dataset: MarketDataset with features and labels.
            class_weights: Optional class weights for imbalanced datasets.

        Returns:
            Dict with training results, best metrics, and checkpoint paths.
        """
        model = model.to(self.device)
        n_samples = len(dataset)

        splitter = WalkForwardSplitter(
            n_splits=self.config.walk_forward_splits,
            train_ratio=self.config.train_ratio,
            val_ratio=self.config.val_ratio,
        )
        splits = splitter.split(n_samples)

        if not splits:
            logger.warning("No valid splits, training on full dataset")
            splits = [(
                np.arange(int(n_samples * 0.8)),
                np.arange(int(n_samples * 0.8), int(n_samples * 0.9)),
                np.arange(int(n_samples * 0.9), n_samples),
            )]

        all_results: List[Dict[str, Any]] = []
        best_overall_loss = float("inf")

        for fold_idx, (train_idx, val_idx, test_idx) in enumerate(splits):
            logger.info(
                f"Walk-forward fold {fold_idx + 1}/{len(splits)}: "
                f"train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}"
            )

            model_copy = type(model)(model.config) if hasattr(model, 'config') else model
            model_copy = model_copy.to(self.device)

            fold_result = self._train_fold(
                model_copy, dataset, train_idx, val_idx, test_idx,
                class_weights, fold_idx,
            )
            all_results.append(fold_result)

            if fold_result["best_val_loss"] < best_overall_loss:
                best_overall_loss = fold_result["best_val_loss"]
                self.checkpointer.save_best(
                    model_copy,
                    fold_result["optimizer"],
                    fold_result["best_epoch"],
                    {"val_loss": best_overall_loss, "fold": fold_idx},
                )
                best_model_state = model_copy.state_dict()

        model.load_state_dict(best_model_state)

        return {
            "folds": all_results,
            "best_val_loss": best_overall_loss,
            "n_folds": len(splits),
            "history": self.metrics_logger.history,
        }

    def _train_fold(
        self,
        model: nn.Module,
        dataset: MarketDataset,
        train_idx: np.ndarray,
        val_idx: np.ndarray,
        test_idx: np.ndarray,
        class_weights: Optional[np.ndarray],
        fold_idx: int,
    ) -> Dict[str, Any]:
        train_loader = DataLoader(
            Subset(dataset, train_idx.tolist()),
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory,
            collate_fn=_collate_dict_batch,
        )
        val_loader = DataLoader(
            Subset(dataset, val_idx.tolist()),
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=self.config.num_workers,
            collate_fn=_collate_dict_batch,
        )

        optimizer = optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        scheduler = self._create_scheduler(optimizer)

        if class_weights is not None:
            weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(self.device)
            criterion = nn.CrossEntropyLoss(
                weight=weight_tensor,
                label_smoothing=self.config.label_smoothing,
            )
        else:
            criterion = nn.CrossEntropyLoss(
                label_smoothing=self.config.label_smoothing,
            )

        early_stopping = EarlyStopping(
            patience=self.config.patience,
            min_delta=self.config.min_delta,
        )

        best_val_loss = float("inf")
        best_epoch = 0
        best_state = None

        scaler = torch.amp.GradScaler("cuda") if self.config.mixed_precision and self.device.type == "cuda" else None

        for epoch in range(self.config.epochs):
            train_loss, train_acc = self._train_epoch(
                model, train_loader, criterion, optimizer, scaler,
            )
            val_loss, val_acc = self._validate_epoch(model, val_loader, criterion)

            metrics = {
                f"fold{fold_idx}_train_loss": train_loss,
                f"fold{fold_idx}_train_acc": train_acc,
                f"fold{fold_idx}_val_loss": val_loss,
                f"fold{fold_idx}_val_acc": val_acc,
            }
            self.metrics_logger.log(epoch, metrics)

            if isinstance(scheduler, optim.lr_scheduler.ReduceLROnPlateau):
                scheduler.step(val_loss)
            elif scheduler is not None:
                scheduler.step()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_epoch = epoch
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

            if early_stopping(val_loss):
                logger.info(f"Early stopping at epoch {epoch}")
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        test_metrics = {}
        if len(test_idx) > 0:
            test_loader = DataLoader(
                Subset(dataset, test_idx.tolist()),
                batch_size=self.config.batch_size,
                shuffle=False,
                collate_fn=_collate_dict_batch,
            )
            test_loss, test_acc = self._validate_epoch(model, test_loader, criterion)
            test_metrics = {"test_loss": test_loss, "test_acc": test_acc}

        return {
            "best_val_loss": best_val_loss,
            "best_epoch": best_epoch,
            "test_metrics": test_metrics,
            "optimizer": optimizer,
        }

    def _train_epoch(
        self,
        model: nn.Module,
        loader: DataLoader,
        criterion: nn.Module,
        optimizer: optim.Optimizer,
        scaler: Optional[torch.amp.GradScaler],
    ) -> Tuple[float, float]:
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for features, labels in loader:
            features = {k: v.to(self.device) for k, v in features.items()}
            labels = labels.to(self.device)

            optimizer.zero_grad()

            if scaler is not None:
                with torch.amp.autocast("cuda"):
                    logits, _ = model(features)
                    loss = criterion(logits, labels)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), self.config.gradient_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                logits, _ = model(features)
                loss = criterion(logits, labels)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), self.config.gradient_clip)
                optimizer.step()

            total_loss += loss.item() * labels.size(0)
            preds = logits.argmax(dim=-1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        avg_loss = total_loss / max(total, 1)
        accuracy = correct / max(total, 1)
        return avg_loss, accuracy

    def _validate_epoch(
        self,
        model: nn.Module,
        loader: DataLoader,
        criterion: nn.Module,
    ) -> Tuple[float, float]:
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for features, labels in loader:
                features = {k: v.to(self.device) for k, v in features.items()}
                labels = labels.to(self.device)

                logits, _ = model(features)
                loss = criterion(logits, labels)

                total_loss += loss.item() * labels.size(0)
                preds = logits.argmax(dim=-1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)

        avg_loss = total_loss / max(total, 1)
        accuracy = correct / max(total, 1)
        return avg_loss, accuracy

    def _create_scheduler(
        self, optimizer: optim.Optimizer
    ) -> Optional[optim.lr_scheduler.LRScheduler]:
        if self.config.lr_scheduler == "cosine":
            return optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=self.config.epochs
            )
        elif self.config.lr_scheduler == "step":
            return optim.lr_scheduler.StepLR(
                optimizer,
                step_size=self.config.lr_step_size,
                gamma=self.config.lr_gamma,
            )
        elif self.config.lr_scheduler == "plateau":
            return optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode="min", patience=5, factor=0.5
            )
        return None

    def compute_class_weights(self, labels: np.ndarray) -> np.ndarray:
        """Compute inverse-frequency class weights for imbalanced datasets."""
        classes, counts = np.unique(labels, return_counts=True)
        n_samples = len(labels)
        n_classes = len(classes)
        weights = n_samples / (n_classes * counts + 1e-10)
        weights = weights / weights.sum() * n_classes
        return weights
