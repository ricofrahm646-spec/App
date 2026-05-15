from dataclasses import dataclass


@dataclass(slots=True)
class ICTStrategyConfig:
    session: str = "New York"
    require_liquidity_sweep: bool = True
    require_displacement: bool = True
    use_order_blocks: bool = True


def describe_strategy(config: ICTStrategyConfig) -> str:
    return (
        "ICT strategy blueprint using liquidity sweeps, displacement and order-block "
        f"confirmation during the {config.session} session."
    )
