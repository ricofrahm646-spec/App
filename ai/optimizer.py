from dataclasses import dataclass


@dataclass(slots=True)
class OptimizationRequest:
    strategy_name: str
    objective: str
    max_trials: int
    walk_forward_folds: int


@dataclass(slots=True)
class OptimizationPlan:
    libraries: list[str]
    safeguards: list[str]
    notes: str


def build_optimization_plan(request: OptimizationRequest) -> OptimizationPlan:
    return OptimizationPlan(
        libraries=["PyTorch", "TensorFlow", "XGBoost", "Optuna"],
        safeguards=[
            "Use walk-forward validation before promoting parameters.",
            "Reject configurations that improve profit while worsening drawdown materially.",
            "Store experiment metadata for reproducibility and overfitting checks.",
        ],
        notes=(
            f"Optimize '{request.strategy_name}' for '{request.objective}' with "
            f"{request.max_trials} trials across {request.walk_forward_folds} folds."
        ),
    )
