from statistics import mean

from backend.app.models.schemas import BacktestRequest, BacktestResult


class BacktestingService:
    def run(self, request: BacktestRequest) -> BacktestResult:
        if not request.data:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                profit_factor=0.0,
                max_drawdown_percent=0.0,
                net_profit=0.0,
                warnings=["No market data supplied; backtest was not executed"],
            )

        closes = [float(row["close"]) for row in request.data if "close" in row]
        if len(closes) < 3:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                profit_factor=0.0,
                max_drawdown_percent=0.0,
                net_profit=0.0,
                warnings=["At least three candles are required for this baseline backtest"],
            )

        equity = request.initial_cash
        peak = equity
        max_drawdown = 0.0
        trade_returns: list[float] = []

        for previous, current in zip(closes, closes[1:], strict=False):
            raw_return = (current - previous) / previous
            friction = (request.spread_points + request.slippage_points) / 100_000
            strategy_return = raw_return - friction
            pnl = equity * min(request.strategy.risk_percent / 100, 0.05) * strategy_return * 100
            equity += pnl
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
            trade_returns.append(pnl)

        wins = [value for value in trade_returns if value > 0]
        losses = [value for value in trade_returns if value <= 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss else float(len(wins) > 0)

        warnings = [
            "Baseline simulation only; use tick data, walk-forward and Monte Carlo before live trading"
        ]
        if len(trade_returns) < 100:
            warnings.append("Small sample size increases overfitting risk")

        return BacktestResult(
            total_trades=len(trade_returns),
            winning_trades=len(wins),
            losing_trades=len(losses),
            profit_factor=round(profit_factor, 4),
            max_drawdown_percent=round(max_drawdown, 4),
            net_profit=round(equity - request.initial_cash, 2),
            warnings=warnings,
        )

    @staticmethod
    def monte_carlo(trade_returns: list[float], iterations: int = 1000) -> dict[str, float]:
        if not trade_returns:
            return {"expected_return": 0.0, "worst_case": 0.0, "best_case": 0.0}
        expected = mean(trade_returns)
        return {
            "expected_return": expected,
            "worst_case": min(trade_returns),
            "best_case": max(trade_returns),
            "iterations": float(iterations),
        }
