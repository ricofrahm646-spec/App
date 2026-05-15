from dataclasses import dataclass


@dataclass
class StrategyProfile:
    name: str
    category: str
    enabled: bool
    score: float


class StrategyRegistry:
    def __init__(self) -> None:
        self._strategies = [
            StrategyProfile("Gold Scalping Core", "scalping", True, 0.72),
            StrategyProfile("ICT Liquidity Sweep", "ict", True, 0.68),
            StrategyProfile("Mean Reversion FX", "mean_reversion", False, 0.41),
        ]

    def list_strategies(self) -> list[StrategyProfile]:
        return self._strategies

    def prioritize(self) -> list[StrategyProfile]:
        return sorted(self._strategies, key=lambda item: item.score, reverse=True)
