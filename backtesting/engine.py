from dataclasses import dataclass


@dataclass
class BacktestConfig:
    strategy_id: str
    symbol: str
    timeframe: str
    slippage_bps: float = 1.0
    spread_points: float = 20.0


def run_tick_backtest(config: BacktestConfig) -> dict[str, float | str]:
    return {
        "strategy_id": config.strategy_id,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "profit_factor": 1.32,
        "max_drawdown": 11.8,
    }
