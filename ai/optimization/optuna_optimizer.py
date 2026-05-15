import optuna


def objective(trial: optuna.Trial) -> float:
    risk_penalty = trial.suggest_float("risk_penalty", 0.1, 1.5)
    momentum_weight = trial.suggest_float("momentum_weight", 0.1, 2.0)
    # Placeholder for backtest score function.
    return (1.7 * momentum_weight) - (0.8 * risk_penalty)


def run_study(trials: int = 50) -> optuna.study.Study:
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=trials)
    return study
