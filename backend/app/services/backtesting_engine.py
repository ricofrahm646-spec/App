from app.models.schemas import BacktestRequest, BacktestResult


class BacktestingEngine:
    """
    Backtesting facade.
    Replace placeholders with concrete vectorbt/backtrader pipelines.
    """

    def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        notes = [
            "Tick simulation pipeline placeholder initialized.",
            "Walk-forward mode enabled." if request.walk_forward else "Walk-forward mode disabled.",
            f"Monte Carlo runs configured: {request.monte_carlo_runs}.",
            "Slippage and spread simulation hooks available.",
        ]

        return BacktestResult(
            strategy_name=request.strategy_name,
            symbol=request.symbol,
            winrate=0.53,
            profit_factor=1.35,
            max_drawdown=0.12,
            notes=notes,
        )
