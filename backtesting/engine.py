from dataclasses import dataclass


@dataclass(slots=True)
class BacktestScenario:
    symbol: str
    timeframe: str
    spread_bps: float
    slippage_bps: float


def supported_validations() -> list[str]:
    return [
        "tick-backtesting",
        "walk-forward-analysis",
        "monte-carlo-analysis",
        "multi-timeframe-testing",
        "slippage-simulation",
        "spread-simulation",
    ]
