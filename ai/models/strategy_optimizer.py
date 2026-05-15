"""
JARVIS AI Trading OS - Strategy Optimizer

Hyperparameter optimization for trading strategies using Optuna, walk-forward
analysis, anti-overfitting measures, and a genetic algorithm fallback.
"""

from __future__ import annotations

import copy
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Sequence

import numpy as np

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
except ImportError:
    optuna = None  # type: ignore[assignment]

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParameterRange:
    name: str
    low: float
    high: float
    step: Optional[float] = None
    is_int: bool = False


@dataclass
class BacktestResult:
    sharpe_ratio: float
    total_return: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    equity_curve: Optional[pd.Series] = None


@dataclass
class OptimizationResult:
    best_params: dict[str, Any]
    best_score: float
    all_trials: list[dict[str, Any]] = field(default_factory=list)
    in_sample_score: float = 0.0
    out_of_sample_score: float = 0.0
    walk_forward_scores: list[float] = field(default_factory=list)
    overfitting_score: float = 0.0


# ---------------------------------------------------------------------------
# Protocol for the backtest callable
# ---------------------------------------------------------------------------

class BacktestRunner(Protocol):
    def __call__(
        self,
        params: dict[str, Any],
        data: pd.DataFrame,
    ) -> BacktestResult: ...


# ---------------------------------------------------------------------------
# Optuna-based optimizer
# ---------------------------------------------------------------------------

class StrategyOptimizer:
    """
    Optimizes strategy parameters using Optuna with walk-forward analysis
    and anti-overfitting safeguards.
    """

    def __init__(
        self,
        backtest_fn: BacktestRunner,
        param_ranges: list[ParameterRange],
        data: pd.DataFrame,
        n_trials: int = 200,
        n_splits: int = 5,
        out_of_sample_pct: float = 0.3,
        objective_metric: str = "sharpe_ratio",
        seed: int = 42,
    ) -> None:
        if optuna is None:
            raise ImportError("Optuna is required: pip install optuna")
        self.backtest_fn = backtest_fn
        self.param_ranges = param_ranges
        self.data = data
        self.n_trials = n_trials
        self.n_splits = n_splits
        self.oos_pct = out_of_sample_pct
        self.objective_metric = objective_metric
        self.seed = seed
        self._results: list[dict[str, Any]] = []

    def _sample_params(self, trial: optuna.Trial) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for pr in self.param_ranges:
            if pr.is_int:
                params[pr.name] = trial.suggest_int(
                    pr.name, int(pr.low), int(pr.high), step=int(pr.step) if pr.step else 1,
                )
            else:
                params[pr.name] = trial.suggest_float(
                    pr.name, pr.low, pr.high, step=pr.step,
                )
        return params

    def _objective(self, trial: optuna.Trial) -> float:
        params = self._sample_params(trial)
        split = int(len(self.data) * (1 - self.oos_pct))
        in_sample = self.data.iloc[:split]

        result = self.backtest_fn(params, in_sample)
        score = getattr(result, self.objective_metric, result.sharpe_ratio)

        self._results.append({**params, "score": score, "num_trades": result.num_trades})
        return float(score)

    def optimize(self) -> OptimizationResult:
        sampler = optuna.samplers.TPESampler(seed=self.seed)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(self._objective, n_trials=self.n_trials, show_progress_bar=False)

        best_params = study.best_params

        split = int(len(self.data) * (1 - self.oos_pct))
        is_result = self.backtest_fn(best_params, self.data.iloc[:split])
        oos_result = self.backtest_fn(best_params, self.data.iloc[split:])

        is_score = getattr(is_result, self.objective_metric, is_result.sharpe_ratio)
        oos_score = getattr(oos_result, self.objective_metric, oos_result.sharpe_ratio)

        wf_scores = self._walk_forward(best_params)
        overfitting = self._overfitting_score(is_score, oos_score)

        return OptimizationResult(
            best_params=best_params,
            best_score=study.best_value,
            all_trials=self._results,
            in_sample_score=float(is_score),
            out_of_sample_score=float(oos_score),
            walk_forward_scores=wf_scores,
            overfitting_score=overfitting,
        )

    def _walk_forward(self, params: dict[str, Any]) -> list[float]:
        n = len(self.data)
        fold_size = n // self.n_splits
        scores: list[float] = []

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = min(test_start + fold_size, n)
            test_data = self.data.iloc[test_start:test_end]
            if len(test_data) < 20:
                continue
            result = self.backtest_fn(params, test_data)
            scores.append(getattr(result, self.objective_metric, result.sharpe_ratio))

        return scores

    @staticmethod
    def _overfitting_score(is_score: float, oos_score: float) -> float:
        if is_score == 0:
            return 0.0
        return max(0.0, 1.0 - (oos_score / is_score))

    def cross_validate(self, params: dict[str, Any]) -> list[float]:
        n = len(self.data)
        fold_size = n // self.n_splits
        scores: list[float] = []

        for i in range(self.n_splits):
            val_start = i * fold_size
            val_end = min(val_start + fold_size, n)
            val_data = self.data.iloc[val_start:val_end]
            if len(val_data) < 20:
                continue
            result = self.backtest_fn(params, val_data)
            scores.append(getattr(result, self.objective_metric, result.sharpe_ratio))

        return scores


# ---------------------------------------------------------------------------
# Genetic Algorithm Optimizer
# ---------------------------------------------------------------------------

@dataclass
class Individual:
    genes: dict[str, float]
    fitness: float = 0.0


class GeneticAlgorithm:
    """
    Evolutionary optimizer for strategy parameters.

    Uses tournament selection, uniform crossover, and Gaussian mutation.
    """

    def __init__(
        self,
        backtest_fn: BacktestRunner,
        param_ranges: list[ParameterRange],
        data: pd.DataFrame,
        population_size: int = 50,
        generations: int = 100,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        tournament_size: int = 3,
        elitism: int = 2,
        objective_metric: str = "sharpe_ratio",
        seed: int = 42,
    ) -> None:
        self.backtest_fn = backtest_fn
        self.param_ranges = param_ranges
        self.data = data
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.elitism = elitism
        self.objective_metric = objective_metric
        self._rng = random.Random(seed)
        self._np_rng = np.random.RandomState(seed)
        self._history: list[dict[str, Any]] = []

    def _random_individual(self) -> Individual:
        genes: dict[str, float] = {}
        for pr in self.param_ranges:
            if pr.step:
                steps = int((pr.high - pr.low) / pr.step)
                val = pr.low + self._rng.randint(0, steps) * pr.step
            else:
                val = self._rng.uniform(pr.low, pr.high)
            if pr.is_int:
                val = round(val)
            genes[pr.name] = val
        return Individual(genes=genes)

    def _evaluate(self, individual: Individual) -> float:
        result = self.backtest_fn(individual.genes, self.data)
        fitness = float(getattr(result, self.objective_metric, result.sharpe_ratio))
        individual.fitness = fitness
        return fitness

    def _tournament_select(self, population: list[Individual]) -> Individual:
        contestants = self._rng.sample(population, min(self.tournament_size, len(population)))
        return max(contestants, key=lambda ind: ind.fitness)

    def _crossover(self, parent_a: Individual, parent_b: Individual) -> Individual:
        child_genes: dict[str, float] = {}
        for pr in self.param_ranges:
            if self._rng.random() < 0.5:
                child_genes[pr.name] = parent_a.genes[pr.name]
            else:
                child_genes[pr.name] = parent_b.genes[pr.name]
        return Individual(genes=child_genes)

    def _mutate(self, individual: Individual) -> Individual:
        mutated = copy.deepcopy(individual)
        for pr in self.param_ranges:
            if self._rng.random() < self.mutation_rate:
                spread = (pr.high - pr.low) * 0.1
                delta = self._np_rng.normal(0, spread)
                new_val = float(np.clip(mutated.genes[pr.name] + delta, pr.low, pr.high))
                if pr.step:
                    new_val = pr.low + round((new_val - pr.low) / pr.step) * pr.step
                if pr.is_int:
                    new_val = round(new_val)
                mutated.genes[pr.name] = new_val
        return mutated

    def evolve(self) -> OptimizationResult:
        population = [self._random_individual() for _ in range(self.population_size)]
        for ind in population:
            self._evaluate(ind)

        best_ever = max(population, key=lambda i: i.fitness)

        for gen in range(self.generations):
            population.sort(key=lambda i: i.fitness, reverse=True)
            new_pop = population[: self.elitism]

            while len(new_pop) < self.population_size:
                parent_a = self._tournament_select(population)
                parent_b = self._tournament_select(population)
                if self._rng.random() < self.crossover_rate:
                    child = self._crossover(parent_a, parent_b)
                else:
                    child = copy.deepcopy(parent_a)
                child = self._mutate(child)
                self._evaluate(child)
                new_pop.append(child)

            population = new_pop
            gen_best = max(population, key=lambda i: i.fitness)
            if gen_best.fitness > best_ever.fitness:
                best_ever = copy.deepcopy(gen_best)

            self._history.append({
                "generation": gen,
                "best_fitness": gen_best.fitness,
                "avg_fitness": float(np.mean([i.fitness for i in population])),
            })

            if gen % 10 == 0:
                logger.info(
                    "Gen %d/%d | Best=%.4f Avg=%.4f",
                    gen, self.generations, gen_best.fitness,
                    self._history[-1]["avg_fitness"],
                )

        return OptimizationResult(
            best_params=best_ever.genes,
            best_score=best_ever.fitness,
            all_trials=self._history,
        )

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)


# ---------------------------------------------------------------------------
# Result comparison utility
# ---------------------------------------------------------------------------

class ResultsTracker:
    """Collects and compares optimization runs."""

    def __init__(self) -> None:
        self._runs: list[OptimizationResult] = []

    def add(self, result: OptimizationResult) -> int:
        self._runs.append(result)
        return len(self._runs) - 1

    @property
    def best(self) -> OptimizationResult:
        if not self._runs:
            raise ValueError("No results tracked yet")
        return max(self._runs, key=lambda r: r.best_score)

    def summary(self) -> pd.DataFrame:
        rows = []
        for idx, run in enumerate(self._runs):
            rows.append({
                "run": idx,
                "best_score": run.best_score,
                "is_score": run.in_sample_score,
                "oos_score": run.out_of_sample_score,
                "overfitting": run.overfitting_score,
                **run.best_params,
            })
        return pd.DataFrame(rows)

    def __len__(self) -> int:
        return len(self._runs)
