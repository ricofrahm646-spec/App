def run_optuna_stub(strategy_id: str) -> dict[str, str]:
    return {
        "strategy_id": strategy_id,
        "engine": "optuna",
        "status": "stub",
    }


def run_genetic_stub(strategy_id: str) -> dict[str, str]:
    return {
        "strategy_id": strategy_id,
        "engine": "genetic",
        "status": "stub",
    }
