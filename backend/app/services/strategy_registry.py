from app.models.strategy import StrategyDefinition, StrategyScore


class StrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, StrategyDefinition] = {}

    def upsert(self, strategy: StrategyDefinition) -> StrategyDefinition:
        self._strategies[strategy.strategy_id] = strategy
        return strategy

    def list_all(self) -> list[StrategyDefinition]:
        return list(self._strategies.values())

    def evaluate(self) -> list[StrategyScore]:
        scores: list[StrategyScore] = []
        for strategy in self._strategies.values():
            base = 0.6 if strategy.enabled else 0.2
            bonus = min(len(strategy.parameters) * 0.05, 0.3)
            scores.append(
                StrategyScore(
                    strategy_id=strategy.strategy_id,
                    score=round(base + bonus, 3),
                    reason="Heuristische Basisbewertung (Platzhalter fuer AI-Ranking).",
                )
            )
        return sorted(scores, key=lambda x: x.score, reverse=True)
