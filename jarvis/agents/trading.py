import yfinance as yf
import pandas as pd
import numpy as np
from jarvis.agents.base import BaseAgent
from typing import Dict, Any

class TradingAgent(BaseAgent):
    def __init__(self):
        super().__init__("Trading")

    async def get_market_data(self, ticker: str, period: str = "1y", interval: str = "1d"):
        try:
            data = yf.download(ticker, period=period, interval=interval)
            return data
        except Exception as e:
            return None

    def backtest_strategy(self, data: pd.DataFrame):
        # Simple SMA Crossover strategy for backtesting
        df = data.copy()
        # Handle MultiIndex if necessary (yfinance sometimes returns MultiIndex columns)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()

        df['Signal'] = 0.0
        df.loc[df.index[20:], 'Signal'] = np.where(df['SMA20'][20:] > df['SMA50'][20:], 1.0, 0.0)
        df['Position'] = df['Signal'].diff()

        # Calculate Win Rate
        trades = []
        entry_price = 0
        for i in range(len(df)):
            pos = df['Position'].iloc[i]
            # Ensure we get a scalar value
            if isinstance(pos, pd.Series): pos = pos.item()

            if pos == 1: # Buy
                close_val = df['Close'].iloc[i]
                if isinstance(close_val, pd.Series): close_val = close_val.item()
                entry_price = close_val
            elif pos == -1 and entry_price != 0: # Sell
                close_val = df['Close'].iloc[i]
                if isinstance(close_val, pd.Series): close_val = close_val.item()
                exit_price = close_val
                trades.append(exit_price > entry_price)
                entry_price = 0

        win_rate = (sum(trades) / len(trades)) * 100 if trades else 0
        return win_rate, len(trades)

    async def find_best_pair(self, tickers: list):
        best_ticker = None
        highest_win_rate = -1

        for ticker in tickers:
            data = await self.get_market_data(ticker)
            if data is not None and not data.empty and len(data) > 50:
                win_rate, num_trades = self.backtest_strategy(data)
                if win_rate > highest_win_rate and num_trades > 0:
                    highest_win_rate = win_rate
                    best_ticker = ticker

        return best_ticker, highest_win_rate

    async def process(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if "best" in task.lower() or "trade" in task.lower():
            tickers = ["BTC-USD", "ETH-USD", "EURUSD=X", "AAPL", "TSLA", "GOOGL"]
            best_ticker, win_rate = await self.find_best_pair(tickers)

            return {
                "output": f"I've analyzed multiple pairs. The best pair currently is {best_ticker} with a backtested win rate of {win_rate:.2f}%. Strategy: SMA Crossover.",
                "data": {
                    "best_ticker": best_ticker,
                    "win_rate": win_rate
                }
            }

        # Default price check
        ticker = "BTC-USD"
        data = await self.get_market_data(ticker, period="1mo")
        if data is not None and not data.empty:
            last_price = data['Close'].iloc[-1]
            if isinstance(last_price, pd.Series): last_price = last_price.item()
            return {
                "output": f"Current price for {ticker} is {float(last_price):.2f}.",
                "data": {"ticker": ticker, "price": float(last_price)}
            }
        return {"output": "Could not retrieve market data."}
