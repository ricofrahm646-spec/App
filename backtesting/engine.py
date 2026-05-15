from dataclasses import dataclass


@dataclass(slots=True)
class BacktestScenario:
    strategy_name: str
    symbol: str
    timeframe: str
    include_tick_data: bool = True
    include_monte_carlo: bool = True
    include_walk_forward: bool = True


@dataclass(slots=True)
class BacktestPlan:
    tools: list[str]
    checks: list[str]
    summary: str


def build_backtest_plan(scenario: BacktestScenario) -> BacktestPlan:
    return BacktestPlan(
        tools=["VectorBT", "Backtrader", "Pandas", "NumPy"],
        checks=[
            "Tick-level replay when supported by the data provider.",
            "Walk-forward splits to reduce overfitting.",
            "Monte Carlo reshuffling for robustness analysis.",
            "Spread and slippage simulation before approval.",
        ],
        summary=(
            f"Backtest '{scenario.strategy_name}' on {scenario.symbol} {scenario.timeframe} "
            f"with tick={scenario.include_tick_data}, monte_carlo={scenario.include_monte_carlo}, "
            f"walk_forward={scenario.include_walk_forward}."
        ),
    )
