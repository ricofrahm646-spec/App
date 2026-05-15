import pandas as pd
import numpy as np

class BacktestingEngine:
    def __init__(self, data_path: str = None):
        self.data = pd.DataFrame()
        if data_path:
            self.load_data(data_path)

    def load_data(self, path):
        # Simulated loading
        self.data = pd.DataFrame({
            'Open': np.random.randn(100) + 100,
            'High': np.random.randn(100) + 101,
            'Low': np.random.randn(100) + 99,
            'Close': np.random.randn(100) + 100
        })

    def run_simple_backtest(self, strategy_logic):
        # Vectorized backtest simulation
        if self.data.empty:
            self.load_data("")

        returns = self.data['Close'].pct_change()
        # Simulated signals
        signals = np.random.choice([0, 1], size=len(returns))
        strategy_returns = returns * signals

        cumulative_returns = (1 + strategy_returns).cumprod()

        return {
            "total_return": cumulative_returns.iloc[-1],
            "win_rate": np.mean(signals == 1),
            "max_drawdown": (cumulative_returns.cummax() - cumulative_returns).max()
        }
