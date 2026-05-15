from pydantic import BaseModel


class BacktestResult(BaseModel):
    strategy_id: str
    trades: int
    winrate: float
    profit_factor: float
    max_drawdown: float
    notes: str


class BacktestingService:
    def run_backtest(self, strategy_id: str, symbol: str, timeframe: str) -> BacktestResult:
        # Placeholder baseline, intended to be replaced with VectorBT/Backtrader pipelines.
        return BacktestResult(
            strategy_id=strategy_id,
            trades=120,
            winrate=54.5,
            profit_factor=1.32,
            max_drawdown=11.8,
            notes=f"Backtest fuer {symbol} {timeframe} abgeschlossen.",
        )
