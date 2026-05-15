from dataclasses import dataclass


@dataclass(slots=True)
class OptimizationStack:
    supervised_models: tuple[str, ...] = ("xgboost", "lightgbm-compatible", "tabular-ensembles")
    reinforcement_learning: tuple[str, ...] = ("ppo", "sac")
    deep_learning: tuple[str, ...] = ("pytorch", "tensorflow")
    search_methods: tuple[str, ...] = ("optuna", "genetic-algorithms")


def training_objectives() -> list[str]:
    return [
        "Detect market regimes before enabling a strategy family",
        "Optimize for robustness instead of peak in-sample return",
        "Penalize unstable drawdown profiles and overfitted parameter sets",
        "Adapt position sizing according to validated risk constraints",
    ]
