from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelCapability:
    name: str
    purpose: str
    enabled: bool


class LearningStack:
    """Describes and coordinates the optional AI/ML engines used by JARVIS."""

    def capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability("PyTorch", "deep reinforcement learning policies", self._can_import("torch")),
            ModelCapability("TensorFlow", "sequence models and regime classifiers", self._can_import("tensorflow")),
            ModelCapability("XGBoost", "tabular signal ranking and feature importance", self._can_import("xgboost")),
            ModelCapability("Optuna", "hyperparameter optimization", self._can_import("optuna")),
            ModelCapability("Genetic Algorithms", "strategy parameter evolution", True),
        ]

    def analyze_trade_outcomes(self, trades: list[dict[str, Any]]) -> dict[str, Any]:
        wins = [trade for trade in trades if float(trade.get("profit", 0)) > 0]
        losses = [trade for trade in trades if float(trade.get("profit", 0)) < 0]
        return {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "recommendations": self._recommendations(wins=wins, losses=losses),
        }

    def detect_market_phase(self, features: dict[str, float]) -> str:
        volatility = features.get("volatility", 0.0)
        trend_strength = features.get("trend_strength", 0.0)
        if trend_strength > 0.65:
            return "trending"
        if volatility > 0.75:
            return "high_volatility"
        if volatility < 0.25 and trend_strength < 0.35:
            return "range"
        return "transition"

    @staticmethod
    def _can_import(module_name: str) -> bool:
        try:
            __import__(module_name)
        except ImportError:
            return False
        return True

    @staticmethod
    def _recommendations(*, wins: list[dict[str, Any]], losses: list[dict[str, Any]]) -> list[str]:
        if not wins and not losses:
            return ["No trades available for learning yet."]
        if len(losses) > len(wins):
            return ["Reduce risk per trade and rerun walk-forward validation before live deployment."]
        return ["Keep current risk profile and monitor for regime changes."]
