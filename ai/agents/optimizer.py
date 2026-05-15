"""
JARVIS Strategy Optimizer - Uses Optuna + Genetic Algorithms to optimize strategies
"""
from __future__ import annotations

import random
import copy
from typing import Callable, Dict, List, Optional, Tuple, Any

import numpy as np
from loguru import logger

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _OPTUNA_AVAILABLE = True
except ImportError:
    _OPTUNA_AVAILABLE = False
    logger.warning("optuna not installed – Optuna-based optimisation unavailable")


# ---------------------------------------------------------------------------
# Helper: build an Optuna trial from a param_space dict
# ---------------------------------------------------------------------------

def _suggest_params(trial: "optuna.Trial", param_space: Dict) -> Dict:
    """Map a param_space dict to Optuna trial suggestions.

    Each key maps to a dict with keys:
        type:  "int" | "float" | "categorical"
        low:   lower bound (int/float)
        high:  upper bound (int/float)
        step:  optional step (int/float)
        log:   optional bool – use log scale (float only)
        choices: list of values (categorical only)
    """
    params = {}
    for name, spec in param_space.items():
        ptype = spec.get("type", "float")
        if ptype == "int":
            params[name] = trial.suggest_int(
                name, spec["low"], spec["high"], step=spec.get("step", 1)
            )
        elif ptype == "float":
            params[name] = trial.suggest_float(
                name, spec["low"], spec["high"],
                step=spec.get("step"),
                log=spec.get("log", False),
            )
        elif ptype == "categorical":
            params[name] = trial.suggest_categorical(name, spec["choices"])
        else:
            raise ValueError(f"Unknown param type: {ptype!r} for param {name!r}")
    return params


# ---------------------------------------------------------------------------
# StrategyOptimizer
# ---------------------------------------------------------------------------

class StrategyOptimizer:
    """Multi-objective strategy optimizer using Optuna and a genetic algorithm."""

    def __init__(self):
        if not _OPTUNA_AVAILABLE:
            logger.warning("Optuna not available – only genetic_algorithm will work.")

    # ------------------------------------------------------------------
    # Single-objective Optuna optimisation
    # ------------------------------------------------------------------

    def optimize(
        self,
        objective_fn: Callable[[Dict], float],
        param_space:  Dict,
        n_trials:     int = 100,
        direction:    str = "maximize",
        sampler:      Optional[Any] = None,
        pruner:       Optional[Any] = None,
        study_name:   str = "jarvis_study",
        timeout:      Optional[float] = None,
    ) -> Dict:
        """Run Optuna single-objective optimisation.

        Args:
            objective_fn: Function accepting a params dict and returning a scalar.
            param_space:  Parameter space definition (see _suggest_params).
            n_trials:     Number of trials to run.
            direction:    "maximize" or "minimize".
            sampler:      Optional Optuna sampler (default: TPESampler).
            pruner:       Optional Optuna pruner.
            study_name:   Name for the Optuna study.
            timeout:      Optional wall-clock timeout in seconds.

        Returns:
            {
              "best_params": dict,
              "best_value":  float,
              "n_trials":    int,
              "study":       optuna.Study,
              "all_trials":  list of (params, value) tuples,
            }
        """
        if not _OPTUNA_AVAILABLE:
            raise RuntimeError("optuna is required for this method")

        if sampler is None:
            sampler = optuna.samplers.TPESampler(seed=42)

        study = optuna.create_study(
            study_name=study_name,
            direction=direction,
            sampler=sampler,
            pruner=pruner,
        )

        def _objective(trial: optuna.Trial) -> float:
            params = _suggest_params(trial, param_space)
            try:
                value = float(objective_fn(params))
            except Exception as exc:
                logger.debug(f"Trial failed: {exc}")
                raise optuna.exceptions.TrialPruned()
            return value

        study.optimize(_objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)

        all_trials = [
            (t.params, t.value)
            for t in study.trials
            if t.state == optuna.trial.TrialState.COMPLETE
        ]

        logger.info(
            f"Optuna ({study_name}): best={study.best_value:.4f} "
            f"after {len(study.trials)} trials"
        )
        return {
            "best_params": study.best_params,
            "best_value":  study.best_value,
            "n_trials":    len(study.trials),
            "study":       study,
            "all_trials":  all_trials,
        }

    # ------------------------------------------------------------------
    # Multi-objective Optuna optimisation
    # ------------------------------------------------------------------

    def multi_objective_optimize(
        self,
        objective_fn: Callable[[Dict], Tuple[float, float]],
        param_space:  Dict,
        n_trials:     int = 100,
        study_name:   str = "jarvis_multi",
        timeout:      Optional[float] = None,
    ) -> Dict:
        """Optimise simultaneously for profit (maximise) and drawdown (minimise).

        objective_fn must return (profit_metric, drawdown_metric).

        Returns:
            {
              "pareto_front": list of (params, [profit, drawdown]),
              "n_trials":     int,
              "study":        optuna.Study,
            }
        """
        if not _OPTUNA_AVAILABLE:
            raise RuntimeError("optuna is required for this method")

        study = optuna.create_study(
            study_name=study_name,
            directions=["maximize", "minimize"],   # profit up, drawdown down
            sampler=optuna.samplers.NSGAIISampler(seed=42),
        )

        def _objective(trial: optuna.Trial) -> Tuple[float, float]:
            params = _suggest_params(trial, param_space)
            try:
                profit, drawdown = objective_fn(params)
            except Exception as exc:
                logger.debug(f"Multi-obj trial failed: {exc}")
                raise optuna.exceptions.TrialPruned()
            return float(profit), float(drawdown)

        study.optimize(_objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)

        pareto = [
            (t.params, list(t.values))
            for t in study.best_trials
        ]
        logger.info(f"Multi-obj ({study_name}): {len(pareto)} Pareto-optimal solutions found")
        return {
            "pareto_front": pareto,
            "n_trials":     len(study.trials),
            "study":        study,
        }

    # ------------------------------------------------------------------
    # Genetic Algorithm
    # ------------------------------------------------------------------

    def genetic_algorithm(
        self,
        evaluate_fn:      Callable[[Dict], float],
        param_ranges:     Dict,
        generations:      int  = 50,
        population_size:  int  = 100,
        mutation_rate:    float= 0.15,
        crossover_rate:   float= 0.75,
        elite_fraction:   float= 0.10,
        tournament_size:  int  = 5,
        seed:             int  = 42,
        maximize:         bool = True,
    ) -> Dict:
        """Genetic algorithm optimisation.

        param_ranges format:
            { param_name: { "type": "int"|"float"|"categorical",
                             "low": ..., "high": ..., "step": ...,
                             "choices": [...] } }

        Returns:
            {
              "best_params":   dict,
              "best_fitness":  float,
              "history":       list of per-generation best fitness values,
              "final_population": list of (params, fitness),
            }
        """
        random.seed(seed)
        np.random.seed(seed)

        def _random_individual() -> Dict:
            ind = {}
            for name, spec in param_ranges.items():
                ptype = spec.get("type", "float")
                if ptype == "int":
                    step = spec.get("step", 1)
                    choices = list(range(spec["low"], spec["high"] + 1, step))
                    ind[name] = random.choice(choices)
                elif ptype == "float":
                    lo, hi = spec["low"], spec["high"]
                    step   = spec.get("step")
                    if step:
                        n_steps = int((hi - lo) / step)
                        ind[name] = lo + random.randint(0, n_steps) * step
                    else:
                        if spec.get("log", False):
                            ind[name] = float(np.exp(np.random.uniform(np.log(lo), np.log(hi))))
                        else:
                            ind[name] = random.uniform(lo, hi)
                elif ptype == "categorical":
                    ind[name] = random.choice(spec["choices"])
            return ind

        def _mutate(ind: Dict) -> Dict:
            child = copy.deepcopy(ind)
            for name, spec in param_ranges.items():
                if random.random() > mutation_rate:
                    continue
                ptype = spec.get("type", "float")
                if ptype == "int":
                    step = spec.get("step", 1)
                    lo, hi = spec["low"], spec["high"]
                    choices = list(range(lo, hi + 1, step))
                    child[name] = random.choice(choices)
                elif ptype == "float":
                    lo, hi = spec["low"], spec["high"]
                    step   = spec.get("step")
                    if step:
                        n_steps = int((hi - lo) / step)
                        child[name] = lo + random.randint(0, n_steps) * step
                    else:
                        # Gaussian perturbation within bounds
                        sigma = (hi - lo) * 0.1
                        val   = child[name] + random.gauss(0, sigma)
                        child[name] = float(np.clip(val, lo, hi))
                elif ptype == "categorical":
                    child[name] = random.choice(spec["choices"])
            return child

        def _crossover(p1: Dict, p2: Dict) -> Tuple[Dict, Dict]:
            c1, c2 = copy.deepcopy(p1), copy.deepcopy(p2)
            keys = list(param_ranges.keys())
            if random.random() < crossover_rate and len(keys) > 1:
                point = random.randint(1, len(keys) - 1)
                for k in keys[point:]:
                    c1[k], c2[k] = c2[k], c1[k]
            return c1, c2

        def _tournament(pop_fitness: List[Tuple[Dict, float]]) -> Dict:
            contenders = random.sample(pop_fitness, min(tournament_size, len(pop_fitness)))
            return max(contenders, key=lambda x: x[1] if maximize else -x[1])[0]

        # Initialise population
        population = [_random_individual() for _ in range(population_size)]
        history: List[float] = []
        best_params:  Dict  = {}
        best_fitness: float = -np.inf if maximize else np.inf

        n_elite = max(1, int(population_size * elite_fraction))

        for gen in range(generations):
            # Evaluate
            pop_fitness: List[Tuple[Dict, float]] = []
            for ind in population:
                try:
                    fit = float(evaluate_fn(ind))
                except Exception:
                    fit = -np.inf if maximize else np.inf
                pop_fitness.append((ind, fit))

            # Sort
            pop_fitness.sort(key=lambda x: x[1], reverse=maximize)
            gen_best_fitness = pop_fitness[0][1]
            history.append(gen_best_fitness)

            if (maximize and gen_best_fitness > best_fitness) or \
               (not maximize and gen_best_fitness < best_fitness):
                best_fitness = gen_best_fitness
                best_params  = copy.deepcopy(pop_fitness[0][0])

            if gen % 10 == 0 or gen == generations - 1:
                logger.info(f"GA gen {gen+1}/{generations}: best={gen_best_fitness:.4f}")

            # Elitism
            new_population = [copy.deepcopy(ind) for ind, _ in pop_fitness[:n_elite]]

            # Fill remainder via tournament selection + crossover + mutation
            while len(new_population) < population_size:
                p1 = _tournament(pop_fitness)
                p2 = _tournament(pop_fitness)
                c1, c2 = _crossover(p1, p2)
                new_population.append(_mutate(c1))
                if len(new_population) < population_size:
                    new_population.append(_mutate(c2))

            population = new_population

        final_pop = [(ind, float(evaluate_fn(ind))) for ind in population[:20]]

        return {
            "best_params":      best_params,
            "best_fitness":     best_fitness,
            "history":          history,
            "final_population": final_pop,
        }

    # ------------------------------------------------------------------
    # Walk-forward optimisation
    # ------------------------------------------------------------------

    def walk_forward_optimize(
        self,
        data:          np.ndarray,
        strategy_fn:   Callable[[np.ndarray, Dict], float],
        param_space:   Dict,
        window_size:   int = 252,
        step_size:     int = 63,
        n_trials:      int = 50,
        use_optuna:    bool = True,
    ) -> Dict:
        """Walk-forward optimisation.

        The dataset is split into rolling in-sample (IS) windows followed by
        a fixed out-of-sample (OOS) period of `step_size` bars.

        Args:
            data:         1-D or 2-D numpy array of market data.
            strategy_fn:  Callable(data_slice, params) → scalar performance metric.
            param_space:  Parameter space definition.
            window_size:  Number of bars in the in-sample window.
            step_size:    Number of OOS bars per window.
            n_trials:     Optimisation trials per window.
            use_optuna:   Use Optuna if available, otherwise GA.

        Returns:
            {
              "windows":         list of window dicts (is_start, is_end, oos_end,
                                   best_params, is_metric, oos_metric),
              "avg_oos_metric":  float,
              "std_oos_metric":  float,
              "consistency":     float (pct of profitable OOS windows),
              "all_params":      list of best param dicts per window,
            }
        """
        N = len(data)
        if N < window_size + step_size:
            raise ValueError(
                f"Not enough data: need {window_size + step_size}, got {N}"
            )

        windows = []
        oos_metrics: List[float] = []
        all_params:  List[Dict]  = []

        is_start = 0
        while is_start + window_size + step_size <= N:
            is_end  = is_start + window_size
            oos_end = min(is_end + step_size, N)

            is_data  = data[is_start:is_end]
            oos_data = data[is_end:oos_end]

            def _is_objective(params: Dict) -> float:
                return float(strategy_fn(is_data, params))

            if use_optuna and _OPTUNA_AVAILABLE:
                result     = self.optimize(_is_objective, param_space, n_trials=n_trials)
                best_p     = result["best_params"]
                is_metric  = result["best_value"]
            else:
                result     = self.genetic_algorithm(
                    _is_objective, param_space, generations=20,
                    population_size=max(20, n_trials)
                )
                best_p    = result["best_params"]
                is_metric = result["best_fitness"]

            oos_metric = float(strategy_fn(oos_data, best_p))
            oos_metrics.append(oos_metric)
            all_params.append(best_p)

            windows.append({
                "is_start":  is_start,
                "is_end":    is_end,
                "oos_end":   oos_end,
                "best_params": best_p,
                "is_metric": is_metric,
                "oos_metric": oos_metric,
            })

            logger.info(
                f"WF window [{is_start}:{is_end}:{oos_end}] "
                f"IS={is_metric:.4f} OOS={oos_metric:.4f}"
            )
            is_start += step_size

        oos_arr = np.array(oos_metrics)
        return {
            "windows":        windows,
            "avg_oos_metric": float(oos_arr.mean()),
            "std_oos_metric": float(oos_arr.std()),
            "consistency":    float((oos_arr > 0).mean()),
            "all_params":     all_params,
        }

    # ------------------------------------------------------------------
    # Overfitting detection
    # ------------------------------------------------------------------

    def prevent_overfitting(
        self,
        in_sample_results:  Dict,
        out_sample_results: Dict,
        min_oos_ratio:      float = 0.5,
        max_sharpe_gap:     float = 1.5,
    ) -> bool:
        """Heuristic overfitting check.

        Compares IS and OOS metrics; returns True if the strategy looks sound
        (not overfitted), False if it appears overfitted.

        Checks:
          1. OOS profit_factor / IS profit_factor >= min_oos_ratio
          2. IS sharpe / OOS sharpe <= max_sharpe_gap
          3. OOS win_rate is within a plausible range of IS win_rate
        """
        overfitted = False
        reasons: List[str] = []

        # 1. Profit factor degradation
        is_pf  = float(in_sample_results.get("profit_factor",  1.0))
        oos_pf = float(out_sample_results.get("profit_factor", 0.0))
        if is_pf > 0:
            pf_ratio = oos_pf / (is_pf + 1e-10)
            if pf_ratio < min_oos_ratio:
                overfitted = True
                reasons.append(
                    f"PF degradation: IS={is_pf:.2f} OOS={oos_pf:.2f} ratio={pf_ratio:.2f}"
                )

        # 2. Sharpe ratio gap
        is_sharpe  = float(in_sample_results.get("sharpe_ratio",  0.0))
        oos_sharpe = float(out_sample_results.get("sharpe_ratio", 0.0))
        if oos_sharpe > 0 and is_sharpe > 0:
            sharpe_gap = is_sharpe / (oos_sharpe + 1e-10)
            if sharpe_gap > max_sharpe_gap:
                overfitted = True
                reasons.append(
                    f"Sharpe gap: IS={is_sharpe:.2f} OOS={oos_sharpe:.2f} gap={sharpe_gap:.2f}"
                )
        elif is_sharpe > 0 and oos_sharpe <= 0:
            overfitted = True
            reasons.append(f"OOS Sharpe is non-positive ({oos_sharpe:.2f})")

        # 3. Win-rate plausibility
        is_wr  = float(in_sample_results.get("win_rate",  0.5))
        oos_wr = float(out_sample_results.get("win_rate", 0.5))
        wr_gap = abs(is_wr - oos_wr)
        if wr_gap > 0.20:
            overfitted = True
            reasons.append(
                f"Win-rate gap: IS={is_wr:.2%} OOS={oos_wr:.2%} gap={wr_gap:.2%}"
            )

        # 4. OOS drawdown blow-up
        is_dd  = float(in_sample_results.get("max_drawdown",  0.0))
        oos_dd = float(out_sample_results.get("max_drawdown", 0.0))
        if is_dd > 0 and oos_dd > is_dd * 2:
            overfitted = True
            reasons.append(
                f"DD blow-up: IS={is_dd:.2%} OOS={oos_dd:.2%}"
            )

        if overfitted:
            logger.warning("Overfitting detected: " + " | ".join(reasons))
        else:
            logger.info("Overfitting check passed – strategy appears robust")

        return not overfitted   # True = NOT overfitted (trade allowed)

    # ------------------------------------------------------------------
    # Bayesian hyperparameter search via Optuna (alias)
    # ------------------------------------------------------------------

    def bayesian_optimize(
        self,
        objective_fn: Callable[[Dict], float],
        param_space:  Dict,
        n_trials:     int = 150,
        direction:    str = "maximize",
    ) -> Dict:
        """Alias for Optuna TPE optimisation with a larger default trial count."""
        return self.optimize(
            objective_fn, param_space,
            n_trials=n_trials, direction=direction,
            sampler=optuna.samplers.TPESampler(n_startup_trials=20, seed=42)
            if _OPTUNA_AVAILABLE else None,
        )

    # ------------------------------------------------------------------
    # Grid search (exhaustive, small spaces only)
    # ------------------------------------------------------------------

    def grid_search(
        self,
        objective_fn: Callable[[Dict], float],
        param_grid:   Dict[str, List],
        maximize:     bool = True,
    ) -> Dict:
        """Exhaustive grid search over discrete param combinations.

        param_grid: { param_name: [v1, v2, ...] }
        """
        from itertools import product as iterproduct

        keys   = list(param_grid.keys())
        combos = list(iterproduct(*[param_grid[k] for k in keys]))

        best_params:  Dict  = {}
        best_fitness: float = -np.inf if maximize else np.inf
        all_results: List[Tuple[Dict, float]] = []

        for values in combos:
            params = dict(zip(keys, values))
            try:
                fitness = float(objective_fn(params))
            except Exception:
                fitness = -np.inf if maximize else np.inf

            all_results.append((params, fitness))
            better = fitness > best_fitness if maximize else fitness < best_fitness
            if better:
                best_fitness = fitness
                best_params  = params

        all_results.sort(key=lambda x: x[1], reverse=maximize)
        logger.info(
            f"Grid search: {len(combos)} combos evaluated, best={best_fitness:.4f}"
        )
        return {
            "best_params":  best_params,
            "best_fitness": best_fitness,
            "all_results":  all_results[:50],
            "n_evaluated":  len(combos),
        }
