import pandas as pd
import numpy as np

class BacktestingEngine:
    def __init__(self, data: pd.DataFrame = None):
        self.data = data if data is not None else self._generate_mock_data()

    def _generate_mock_data(self):
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        prices = 100 * (1 + np.random.randn(252) * 0.01).cumprod()
        return pd.DataFrame({'Close': prices}, index=dates)

    def calculate_metrics(self, strategy_returns: pd.Series):
        # Professional Risk Metrics
        total_return = (1 + strategy_returns).prod() - 1
        sharpe_ratio = np.sqrt(252) * strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() != 0 else 0

        downside_returns = strategy_returns[strategy_returns < 0]
        sortino_ratio = np.sqrt(252) * strategy_returns.mean() / downside_returns.std() if len(downside_returns) > 0 and downside_returns.std() != 0 else 0

        cum_returns = (1 + strategy_returns).cumprod()
        max_drawdown = (cum_returns.cummax() - cum_returns).max()

        win_rate = (strategy_returns > 0).mean()
        profit_factor = strategy_returns[strategy_returns > 0].sum() / abs(strategy_returns[strategy_returns < 0].sum()) if strategy_returns[strategy_returns < 0].sum() != 0 else float('inf')

        return {
            "total_return": round(total_return, 4),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "max_drawdown": round(max_drawdown, 4),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2)
        }

    def run_backtest(self, strategy_type="ict"):
        # Simulated strategy signals
        returns = self.data['Close'].pct_change().dropna()
        if strategy_type == "ict":
            signals = (np.random.rand(len(returns)) > 0.6).astype(int)
        else:
            signals = (np.random.rand(len(returns)) > 0.5).astype(int)

        strategy_returns = returns * signals
        return self.calculate_metrics(strategy_returns)
