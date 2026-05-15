"""
Strategy Optimizer
==================

Hyperparameter optimization, genetic algorithm evolution, and feature
importance analysis for trading strategy parameters.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ParameterSpace:
    """Defines the search space for a single parameter."""

    name: str
    param_type: str  # 'int', 'float', 'categorical'
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None
    step: Optional[float] = None
    log_scale: bool = False


@dataclass
class OptimizationResult:
    """Result container for optimization runs."""

    best_params: Dict[str, Any]
    best_score: float
    all_trials: List[Dict[str, Any]]
    optimization_history: List[float]
    overfitting_score: float = 0.0
    robustness_score: float = 0.0
    feature_importance: Optional[Dict[str, float]] = None


class OverfitDetector:
    """Detects overfitting by comparing in-sample and out-of-sample performance."""

    def __init__(
        self,
        is_oos_ratio_threshold: float = 0.5,
        parameter_sensitivity_threshold: float = 0.3,
        min_trades_threshold: int = 30,
    ):
        self.is_oos_ratio_threshold = is_oos_ratio_threshold
        self.param_sensitivity_threshold = parameter_sensitivity_threshold
        self.min_trades_threshold = min_trades_threshold

    def check(
        self,
        in_sample_score: float,
        out_of_sample_score: float,
        num_trades: int,
        param_sensitivity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate whether a strategy is likely overfit.

        Returns a dict with overfitting indicators and an aggregate score 0-1.
        """
        warnings: List[str] = []
        score = 0.0

        if in_sample_score > 0:
            oos_ratio = out_of_sample_score / in_sample_score
        else:
            oos_ratio = 0.0 if out_of_sample_score <= 0 else 1.0

        if oos_ratio < self.is_oos_ratio_threshold:
            degradation = 1.0 - oos_ratio
            score += min(degradation, 0.4)
            warnings.append(
                f"OOS/IS ratio {oos_ratio:.2f} below threshold "
                f"{self.is_oos_ratio_threshold:.2f}"
            )

        if num_trades < self.min_trades_threshold:
            trade_penalty = (self.min_trades_threshold - num_trades) / self.min_trades_threshold
            score += trade_penalty * 0.3
            warnings.append(
                f"Only {num_trades} trades (minimum {self.min_trades_threshold})"
            )

        if param_sensitivity is not None and param_sensitivity > self.param_sensitivity_threshold:
            score += min((param_sensitivity - self.param_sensitivity_threshold), 0.3)
            warnings.append(
                f"High parameter sensitivity: {param_sensitivity:.2f}"
            )

        score = min(score, 1.0)

        return {
            "is_overfit": score > 0.5,
            "overfitting_score": score,
            "oos_is_ratio": oos_ratio,
            "num_trades": num_trades,
            "warnings": warnings,
        }

    def compute_parameter_sensitivity(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        best_params: Dict[str, Any],
        param_spaces: List[ParameterSpace],
        num_perturbations: int = 20,
    ) -> float:
        """
        Measure how sensitive the objective is to small parameter changes.

        Higher values indicate more sensitivity (potential overfitting).
        """
        base_score = objective_fn(best_params)
        if base_score == 0:
            return 0.0

        deviations: List[float] = []
        for _ in range(num_perturbations):
            perturbed = copy.deepcopy(best_params)
            for ps in param_spaces:
                if ps.param_type == "categorical":
                    continue
                current = perturbed.get(ps.name, 0)
                if ps.low is not None and ps.high is not None:
                    param_range = ps.high - ps.low
                    noise = random.gauss(0, param_range * 0.05)
                    new_val = current + noise
                    new_val = max(ps.low, min(ps.high, new_val))
                    if ps.param_type == "int":
                        new_val = int(round(new_val))
                    perturbed[ps.name] = new_val

            try:
                perturbed_score = objective_fn(perturbed)
                deviation = abs(perturbed_score - base_score) / (abs(base_score) + 1e-10)
                deviations.append(deviation)
            except Exception:
                continue

        return float(np.mean(deviations)) if deviations else 0.0


class OptunaOptimizer:
    """Bayesian hyperparameter optimization using Optuna."""

    def __init__(
        self,
        param_spaces: List[ParameterSpace],
        objective_fn: Callable[[Dict[str, Any]], float],
        direction: str = "maximize",
        n_trials: int = 100,
        n_startup_trials: int = 10,
        seed: int = 42,
    ):
        self.param_spaces = param_spaces
        self.objective_fn = objective_fn
        self.direction = direction
        self.n_trials = n_trials
        self.n_startup_trials = n_startup_trials
        self.seed = seed
        self._study = None

    def optimize(self) -> OptimizationResult:
        """Run Optuna optimization."""
        try:
            import optuna

            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            logger.warning("Optuna not installed, falling back to random search")
            return self._random_search()

        sampler = optuna.samplers.TPESampler(
            seed=self.seed, n_startup_trials=self.n_startup_trials
        )
        self._study = optuna.create_study(
            direction=self.direction, sampler=sampler
        )
        self._study.optimize(
            self._optuna_objective, n_trials=self.n_trials, show_progress_bar=False
        )

        all_trials = []
        for trial in self._study.trials:
            all_trials.append({
                "number": trial.number,
                "params": trial.params,
                "value": trial.value,
                "state": str(trial.state),
            })

        history = [
            t.value for t in self._study.trials
            if t.value is not None
        ]

        return OptimizationResult(
            best_params=self._study.best_params,
            best_score=self._study.best_value,
            all_trials=all_trials,
            optimization_history=history,
        )

    def _optuna_objective(self, trial) -> float:
        import optuna

        params: Dict[str, Any] = {}
        for ps in self.param_spaces:
            if ps.param_type == "int":
                params[ps.name] = trial.suggest_int(
                    ps.name, int(ps.low), int(ps.high),
                    step=int(ps.step) if ps.step else 1,
                    log=ps.log_scale,
                )
            elif ps.param_type == "float":
                params[ps.name] = trial.suggest_float(
                    ps.name, ps.low, ps.high,
                    step=ps.step,
                    log=ps.log_scale,
                )
            elif ps.param_type == "categorical":
                params[ps.name] = trial.suggest_categorical(ps.name, ps.choices)

        try:
            score = self.objective_fn(params)
        except Exception as e:
            logger.warning(f"Trial {trial.number} failed: {e}")
            raise optuna.TrialPruned()

        return score

    def _random_search(self) -> OptimizationResult:
        """Fallback random search when Optuna is unavailable."""
        best_score = float("-inf") if self.direction == "maximize" else float("inf")
        best_params: Dict[str, Any] = {}
        all_trials: List[Dict[str, Any]] = []
        history: List[float] = []

        for i in range(self.n_trials):
            params = self._sample_random_params()
            try:
                score = self.objective_fn(params)
            except Exception:
                continue

            all_trials.append({"number": i, "params": params, "value": score})
            history.append(score)

            is_better = (
                score > best_score
                if self.direction == "maximize"
                else score < best_score
            )
            if is_better:
                best_score = score
                best_params = params

        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_trials=all_trials,
            optimization_history=history,
        )

    def _sample_random_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        for ps in self.param_spaces:
            if ps.param_type == "int":
                step = int(ps.step) if ps.step else 1
                params[ps.name] = random.randrange(int(ps.low), int(ps.high) + 1, step)
            elif ps.param_type == "float":
                if ps.log_scale and ps.low > 0:
                    log_val = random.uniform(np.log(ps.low), np.log(ps.high))
                    params[ps.name] = float(np.exp(log_val))
                else:
                    params[ps.name] = random.uniform(ps.low, ps.high)
            elif ps.param_type == "categorical":
                params[ps.name] = random.choice(ps.choices)
        return params


@dataclass
class Individual:
    """A single individual in the genetic algorithm population."""

    genes: Dict[str, Any]
    fitness: float = 0.0


class GeneticOptimizer:
    """Genetic algorithm for strategy parameter evolution."""

    def __init__(
        self,
        param_spaces: List[ParameterSpace],
        fitness_fn: Callable[[Dict[str, Any]], float],
        population_size: int = 50,
        generations: int = 100,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        elitism_ratio: float = 0.1,
        tournament_size: int = 3,
        seed: int = 42,
    ):
        self.param_spaces = param_spaces
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elitism_ratio = elitism_ratio
        self.tournament_size = tournament_size
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)

    def optimize(self) -> OptimizationResult:
        """Run genetic algorithm optimization."""
        population = self._initialize_population()
        self._evaluate_population(population)

        best_individual = max(population, key=lambda ind: ind.fitness)
        history: List[float] = [best_individual.fitness]
        all_trials: List[Dict[str, Any]] = []

        stagnation_counter = 0
        prev_best = best_individual.fitness

        for gen in range(self.generations):
            elites = self._select_elites(population)
            offspring: List[Individual] = list(elites)

            while len(offspring) < self.population_size:
                parent1 = self._tournament_select(population)
                parent2 = self._tournament_select(population)

                if self.rng.random() < self.crossover_rate:
                    child1, child2 = self._crossover(parent1, parent2)
                else:
                    child1 = Individual(genes=copy.deepcopy(parent1.genes))
                    child2 = Individual(genes=copy.deepcopy(parent2.genes))

                self._mutate(child1)
                self._mutate(child2)
                offspring.extend([child1, child2])

            population = offspring[: self.population_size]
            self._evaluate_population(population)

            gen_best = max(population, key=lambda ind: ind.fitness)
            if gen_best.fitness > best_individual.fitness:
                best_individual = copy.deepcopy(gen_best)
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            history.append(best_individual.fitness)

            for ind in population:
                all_trials.append({
                    "generation": gen,
                    "params": copy.deepcopy(ind.genes),
                    "value": ind.fitness,
                })

            if stagnation_counter > 20:
                self.mutation_rate = min(self.mutation_rate * 1.5, 0.5)
                stagnation_counter = 0
                logger.info(
                    f"Gen {gen}: Increased mutation rate to {self.mutation_rate:.3f}"
                )

            if gen % 10 == 0:
                logger.info(
                    f"Gen {gen}/{self.generations}: best={best_individual.fitness:.4f}"
                )

            prev_best = best_individual.fitness

        return OptimizationResult(
            best_params=best_individual.genes,
            best_score=best_individual.fitness,
            all_trials=all_trials,
            optimization_history=history,
        )

    def _initialize_population(self) -> List[Individual]:
        population = []
        for _ in range(self.population_size):
            genes: Dict[str, Any] = {}
            for ps in self.param_spaces:
                if ps.param_type == "int":
                    genes[ps.name] = self.rng.randint(int(ps.low), int(ps.high))
                elif ps.param_type == "float":
                    if ps.log_scale and ps.low > 0:
                        log_val = self.rng.uniform(np.log(ps.low), np.log(ps.high))
                        genes[ps.name] = float(np.exp(log_val))
                    else:
                        genes[ps.name] = self.rng.uniform(ps.low, ps.high)
                elif ps.param_type == "categorical":
                    genes[ps.name] = self.rng.choice(ps.choices)
            population.append(Individual(genes=genes))
        return population

    def _evaluate_population(self, population: List[Individual]) -> None:
        for ind in population:
            if ind.fitness == 0.0:
                try:
                    ind.fitness = self.fitness_fn(ind.genes)
                except Exception as e:
                    logger.warning(f"Fitness evaluation failed: {e}")
                    ind.fitness = float("-inf")

    def _select_elites(self, population: List[Individual]) -> List[Individual]:
        sorted_pop = sorted(population, key=lambda ind: ind.fitness, reverse=True)
        n_elites = max(1, int(self.population_size * self.elitism_ratio))
        return [copy.deepcopy(ind) for ind in sorted_pop[:n_elites]]

    def _tournament_select(self, population: List[Individual]) -> Individual:
        tournament = self.rng.sample(
            population, min(self.tournament_size, len(population))
        )
        return max(tournament, key=lambda ind: ind.fitness)

    def _crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[Individual, Individual]:
        child1_genes: Dict[str, Any] = {}
        child2_genes: Dict[str, Any] = {}

        for ps in self.param_spaces:
            if ps.param_type in ("int", "float"):
                v1 = parent1.genes[ps.name]
                v2 = parent2.genes[ps.name]
                alpha = self.rng.uniform(-0.25, 1.25)
                c1 = v1 + alpha * (v2 - v1)
                c2 = v2 + alpha * (v1 - v2)

                if ps.low is not None:
                    c1 = max(ps.low, min(ps.high, c1))
                    c2 = max(ps.low, min(ps.high, c2))

                if ps.param_type == "int":
                    c1, c2 = int(round(c1)), int(round(c2))

                child1_genes[ps.name] = c1
                child2_genes[ps.name] = c2
            else:
                if self.rng.random() < 0.5:
                    child1_genes[ps.name] = parent1.genes[ps.name]
                    child2_genes[ps.name] = parent2.genes[ps.name]
                else:
                    child1_genes[ps.name] = parent2.genes[ps.name]
                    child2_genes[ps.name] = parent1.genes[ps.name]

        return Individual(genes=child1_genes), Individual(genes=child2_genes)

    def _mutate(self, individual: Individual) -> None:
        for ps in self.param_spaces:
            if self.rng.random() > self.mutation_rate:
                continue

            if ps.param_type == "int":
                span = int(ps.high) - int(ps.low)
                delta = self.rng.randint(-max(1, span // 5), max(1, span // 5))
                new_val = individual.genes[ps.name] + delta
                individual.genes[ps.name] = max(int(ps.low), min(int(ps.high), new_val))
            elif ps.param_type == "float":
                span = ps.high - ps.low
                delta = self.rng.gauss(0, span * 0.1)
                new_val = individual.genes[ps.name] + delta
                individual.genes[ps.name] = max(ps.low, min(ps.high, new_val))
            elif ps.param_type == "categorical":
                individual.genes[ps.name] = self.rng.choice(ps.choices)

        individual.fitness = 0.0


class XGBoostFeatureAnalyzer:
    """XGBoost-based feature importance analysis for signal filtering."""

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        importance_threshold: float = 0.01,
        seed: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.importance_threshold = importance_threshold
        self.seed = seed
        self._model = None
        self._feature_names: List[str] = []

    def fit(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Train XGBoost model and extract feature importances.

        Args:
            features: Feature matrix (n_samples, n_features).
            labels: Target labels (n_samples,).
            feature_names: Optional list of feature names.

        Returns:
            Dict mapping feature names to importance scores.
        """
        try:
            import xgboost as xgb
        except ImportError:
            logger.warning("XGBoost not installed, using fallback importance")
            return self._fallback_importance(features, labels, feature_names)

        n_features = features.shape[1]
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(n_features)]
        self._feature_names = feature_names

        unique_labels = np.unique(labels)
        n_classes = len(unique_labels)

        params = {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "random_state": self.seed,
            "n_jobs": -1,
            "use_label_encoder": False,
        }

        if n_classes == 2:
            self._model = xgb.XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                **params,
            )
        elif n_classes > 2:
            self._model = xgb.XGBClassifier(
                objective="multi:softprob",
                eval_metric="mlogloss",
                num_class=n_classes,
                **params,
            )
        else:
            self._model = xgb.XGBRegressor(
                objective="reg:squarederror",
                eval_metric="rmse",
                **params,
            )

        self._model.fit(features, labels)

        raw_importance = self._model.feature_importances_
        importance_dict = {
            name: float(imp)
            for name, imp in zip(feature_names, raw_importance)
        }

        total = sum(importance_dict.values())
        if total > 0:
            importance_dict = {k: v / total for k, v in importance_dict.items()}

        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

    def get_important_features(
        self, importance: Dict[str, float]
    ) -> List[str]:
        """Return features above the importance threshold."""
        return [
            name
            for name, score in importance.items()
            if score >= self.importance_threshold
        ]

    def filter_features(
        self,
        features: np.ndarray,
        importance: Dict[str, float],
        feature_names: List[str],
    ) -> Tuple[np.ndarray, List[str]]:
        """Remove unimportant features from the feature matrix."""
        important = set(self.get_important_features(importance))
        mask = [i for i, name in enumerate(feature_names) if name in important]
        filtered_names = [feature_names[i] for i in mask]
        filtered_features = features[:, mask]
        return filtered_features, filtered_names

    def _fallback_importance(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Correlation-based feature importance when XGBoost is unavailable."""
        n_features = features.shape[1]
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(n_features)]

        importances: Dict[str, float] = {}
        for i, name in enumerate(feature_names):
            corr = abs(np.corrcoef(features[:, i], labels)[0, 1])
            importances[name] = 0.0 if np.isnan(corr) else float(corr)

        total = sum(importances.values())
        if total > 0:
            importances = {k: v / total for k, v in importances.items()}

        return dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

    def cross_validate_importance(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: Optional[List[str]] = None,
        n_folds: int = 5,
    ) -> Dict[str, Dict[str, float]]:
        """
        Cross-validated feature importance with mean and std.

        Returns dict mapping feature names to {'mean': ..., 'std': ...}.
        """
        n_samples = features.shape[0]
        fold_size = n_samples // n_folds
        all_importances: Dict[str, List[float]] = {}

        for fold in range(n_folds):
            start = fold * fold_size
            end = start + fold_size if fold < n_folds - 1 else n_samples

            mask = np.ones(n_samples, dtype=bool)
            mask[start:end] = False
            train_x, train_y = features[mask], labels[mask]

            importance = self.fit(train_x, train_y, feature_names)
            for name, score in importance.items():
                all_importances.setdefault(name, []).append(score)

        result: Dict[str, Dict[str, float]] = {}
        for name, scores in all_importances.items():
            result[name] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
            }

        return result


class StrategyOptimizer:
    """
    Unified strategy optimizer combining Optuna, GA, and XGBoost analysis.

    Provides a single interface for optimizing strategy parameters with
    overfitting detection and feature importance analysis.
    """

    def __init__(
        self,
        param_spaces: List[ParameterSpace],
        objective_fn: Callable[[Dict[str, Any]], float],
        method: str = "optuna",
        n_trials: int = 100,
        seed: int = 42,
    ):
        self.param_spaces = param_spaces
        self.objective_fn = objective_fn
        self.method = method
        self.n_trials = n_trials
        self.seed = seed
        self.overfit_detector = OverfitDetector()

    def optimize(
        self,
        validation_fn: Optional[Callable[[Dict[str, Any]], float]] = None,
    ) -> OptimizationResult:
        """
        Run optimization with overfitting detection.

        Args:
            validation_fn: Optional out-of-sample evaluation function.
                           If provided, overfitting analysis is performed.
        """
        if self.method == "optuna":
            optimizer = OptunaOptimizer(
                param_spaces=self.param_spaces,
                objective_fn=self.objective_fn,
                n_trials=self.n_trials,
                seed=self.seed,
            )
        elif self.method == "genetic":
            optimizer = GeneticOptimizer(
                param_spaces=self.param_spaces,
                fitness_fn=self.objective_fn,
                generations=self.n_trials,
                seed=self.seed,
            )
        else:
            raise ValueError(f"Unknown method: {self.method}. Use 'optuna' or 'genetic'.")

        result = optimizer.optimize()

        if validation_fn is not None:
            oos_score = validation_fn(result.best_params)

            sensitivity = self.overfit_detector.compute_parameter_sensitivity(
                self.objective_fn, result.best_params, self.param_spaces
            )

            overfit_check = self.overfit_detector.check(
                in_sample_score=result.best_score,
                out_of_sample_score=oos_score,
                num_trades=len(result.all_trials),
                param_sensitivity=sensitivity,
            )

            result.overfitting_score = overfit_check["overfitting_score"]
            result.robustness_score = 1.0 - result.overfitting_score

            if overfit_check["is_overfit"]:
                logger.warning(
                    f"Overfitting detected (score={result.overfitting_score:.2f}): "
                    + "; ".join(overfit_check["warnings"])
                )

        return result

    def analyze_features(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Run XGBoost feature importance analysis."""
        analyzer = XGBoostFeatureAnalyzer(seed=self.seed)
        importance = analyzer.fit(features, labels, feature_names)
        return importance
