"""High-level trading simulation and self-improvement workflow."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from memory.memory import MemoryStore
from trading.backtester import BacktestResult, Backtester
from trading.risk_manager import RiskManager
from trading.strategies import (
    BreakoutStrategy,
    EmaStrategy,
    MeanReversionStrategy,
    RsiStrategy,
    TradingStrategy,
)


@dataclass(slots=True)
class TradingSimulationReport:
    """Aggregated report returned after simulation/improvement cycles."""

    cycles: int
    market_seed: int
    initial_strategy_count: int
    final_strategy_count: int
    top_strategy: dict[str, Any] | None
    ranked_results: list[dict[str, Any]]
    improvements: list[dict[str, Any]]


class TradingEngine:
    """Runs backtests, ranks strategies, and applies adaptive parameter tuning."""

    def __init__(self, memory: MemoryStore, *, risk_manager: RiskManager | None = None) -> None:
        self.memory = memory
        self.risk_manager = risk_manager or RiskManager()
        self.backtester = Backtester(risk_manager=self.risk_manager)
        self._strategies: list[TradingStrategy] = [
            EmaStrategy(),
            RsiStrategy(),
            BreakoutStrategy(),
            MeanReversionStrategy(),
        ]

    def generate_synthetic_data(
        self,
        *,
        length: int = 300,
        start_price: float = 100.0,
        drift: float = 0.0004,
        volatility: float = 0.015,
        seed: int = 42,
    ) -> list[float]:
        rng = random.Random(seed)
        prices = [start_price]
        for _ in range(1, length):
            shock = rng.gauss(mu=drift, sigma=volatility)
            next_price = max(1e-6, prices[-1] * (1 + shock))
            prices.append(next_price)
        return prices

    async def run_improvement_cycle(
        self,
        *,
        cycles: int = 3,
        seed: int = 42,
        market_length: int = 320,
    ) -> TradingSimulationReport:
        working: list[TradingStrategy] = list(self._strategies)
        improvements: list[dict[str, Any]] = []
        ranked_payload: list[dict[str, Any]] = []

        for cycle in range(1, cycles + 1):
            prices = self.generate_synthetic_data(length=market_length, seed=seed + cycle)
            results = [self.backtester.run(prices, strategy) for strategy in working]
            ranked = sorted(results, key=lambda item: item.ranking_score, reverse=True)
            ranked_payload = [self._result_to_payload(result) for result in ranked]

            await self.memory.store_knowledge(
                {
                    "cycle": cycle,
                    "type": "trading_cycle_results",
                    "results": ranked_payload,
                },
                tags=["trading", "cycle", f"cycle-{cycle}"],
            )

            if len(ranked) > 1:
                threshold = ranked[0].ranking_score * 0.55
                kept = [result.strategy_name for result in ranked if result.ranking_score >= threshold]
                working = [strategy for strategy in working if strategy.name in kept]

            tuned = self._tune_top_strategies(working, ranked[:2])
            if tuned:
                improvements.extend(tuned)
                for change in tuned:
                    await self.memory.store_improvement(change, tags=["trading", "self-improvement"])

        top_strategy = ranked_payload[0] if ranked_payload else None
        report = TradingSimulationReport(
            cycles=cycles,
            market_seed=seed,
            initial_strategy_count=len(self._strategies),
            final_strategy_count=len(working),
            top_strategy=top_strategy,
            ranked_results=ranked_payload,
            improvements=improvements,
        )
        await self.memory.store_result(
            {
                "agent": "TradingEngine",
                "status": "success",
                "output": {
                    "top_strategy": top_strategy,
                    "final_strategy_count": report.final_strategy_count,
                    "improvements": improvements,
                },
                "metadata": {"cycles": cycles, "seed": seed},
            },
            tags=["trading", "summary"],
        )
        return report

    def _tune_top_strategies(
        self,
        strategies: list[TradingStrategy],
        top_results: list[BacktestResult],
    ) -> list[dict[str, Any]]:
        top_names = {result.strategy_name for result in top_results}
        changes: list[dict[str, Any]] = []
        for strategy in strategies:
            if strategy.name not in top_names:
                continue
            if isinstance(strategy, EmaStrategy):
                old = {"short_period": strategy.short_period, "long_period": strategy.long_period}
                strategy.short_period = max(5, strategy.short_period - 1)
                strategy.long_period = max(strategy.short_period + 4, strategy.long_period - 1)
                changes.append(
                    {
                        "strategy": strategy.name,
                        "action": "parameter_tune",
                        "before": old,
                        "after": {
                            "short_period": strategy.short_period,
                            "long_period": strategy.long_period,
                        },
                    }
                )
            elif isinstance(strategy, RsiStrategy):
                old = {"oversold": strategy.oversold, "overbought": strategy.overbought}
                strategy.oversold = min(40.0, strategy.oversold + 1.0)
                strategy.overbought = max(60.0, strategy.overbought - 1.0)
                changes.append(
                    {
                        "strategy": strategy.name,
                        "action": "parameter_tune",
                        "before": old,
                        "after": {"oversold": strategy.oversold, "overbought": strategy.overbought},
                    }
                )
            elif isinstance(strategy, BreakoutStrategy):
                old = {"lookback": strategy.lookback}
                strategy.lookback = max(10, strategy.lookback - 1)
                changes.append(
                    {
                        "strategy": strategy.name,
                        "action": "parameter_tune",
                        "before": old,
                        "after": {"lookback": strategy.lookback},
                    }
                )
            elif isinstance(strategy, MeanReversionStrategy):
                old = {"threshold": strategy.threshold}
                strategy.threshold = max(0.01, strategy.threshold - 0.002)
                changes.append(
                    {
                        "strategy": strategy.name,
                        "action": "parameter_tune",
                        "before": old,
                        "after": {"threshold": round(strategy.threshold, 4)},
                    }
                )
        return changes

    def _result_to_payload(self, result: BacktestResult) -> dict[str, Any]:
        return {
            "strategy_name": result.strategy_name,
            "total_trades": result.total_trades,
            "winrate": result.winrate,
            "profit_factor": result.profit_factor,
            "max_drawdown": result.max_drawdown,
            "net_profit": result.net_profit,
            "ranking_score": result.ranking_score,
        }

