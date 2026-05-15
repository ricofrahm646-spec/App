class BacktestingService:
    def build_execution_plan(self, *, strategy_name: str, symbol: str, timeframe: str) -> list[str]:
        return [
            f"Load {strategy_name} candles for {symbol} on {timeframe}",
            "Run baseline vectorized backtest with spread and slippage assumptions",
            "Perform walk-forward splits for parameter stability validation",
            "Perform Monte Carlo equity resampling to estimate drawdown resilience",
            "Reject parameter sets that materially degrade across out-of-sample windows",
        ]

    def render_research_note(self, *, strategy_name: str, symbol: str, timeframe: str) -> str:
        return (
            f"# Backtesting plan for {strategy_name}\n\n"
            f"- Symbol: {symbol}\n"
            f"- Timeframe: {timeframe}\n"
            "- Engine targets: VectorBT, Backtrader, NumPy, Pandas\n"
            "- Validation stages: tick replay, walk-forward, Monte Carlo, spread/slippage stress\n"
            "- Acceptance rule: strategy must stay risk-compliant and avoid unstable optimization peaks\n"
        )
