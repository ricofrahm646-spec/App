from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OptimizationCandidate:
    parameters: dict[str, float | int | str]
    score: float
    max_drawdown: float
    profit_factor: float


class Objective(Protocol):
    def __call__(self, parameters: dict[str, float | int | str]) -> OptimizationCandidate:
        ...


class GeneticOptimizer:
    def rank_candidates(self, candidates: list[OptimizationCandidate]) -> list[OptimizationCandidate]:
        return sorted(candidates, key=lambda item: (item.score, -item.max_drawdown), reverse=True)


class OverfittingGuard:
    def accepted(self, in_sample: OptimizationCandidate, out_of_sample: OptimizationCandidate) -> bool:
        if in_sample.score <= 0 or out_of_sample.score <= 0:
            return False
        degradation = (in_sample.score - out_of_sample.score) / in_sample.score
        return degradation <= 0.35 and out_of_sample.max_drawdown <= in_sample.max_drawdown * 1.5
