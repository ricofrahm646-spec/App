from dataclasses import dataclass


@dataclass(slots=True)
class GoldScalpingConfig:
    session: str = "London/New York overlap"
    spread_limit_points: int = 35
    stop_loss_points: int = 250
    take_profit_points: int = 450


def describe_strategy(config: GoldScalpingConfig) -> str:
    return (
        "Gold scalping strategy focused on intraday momentum bursts with a "
        f"{config.session} session bias, spread cap of {config.spread_limit_points} points, "
        f"SL {config.stop_loss_points} and TP {config.take_profit_points}."
    )
