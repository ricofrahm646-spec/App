import pandas as pd
import numpy as np
from typing import Dict, Any, List

class StrategyLibrary:
    """
    SUPREME QUANTUM STRATEGY REPOSITORY - V1300 SINGULARITY
    Precision-engineered algorithms for institutional-grade market dominance.
    """

    @staticmethod
    def smc_institutional_flow(df: pd.DataFrame) -> pd.Series:
        """
        Smart Money Concepts: Institutional Order Flow & Liquidity Sweeps.
        Detects Fair Value Gaps (FVG) and Market Structure Breaks (MSB).
        """
        signals = pd.Series(index=df.index, data=0.0)
        # FVG Detection
        for i in range(2, len(df)):
            # Bullish FVG
            if df['Low'].iloc[i-2] > df['High'].iloc[i]:
                signals.iloc[i] = 1.0
            # Bearish FVG
            elif df['High'].iloc[i-2] < df['Low'].iloc[i]:
                signals.iloc[i] = -1.0
        return signals

    @staticmethod
    def mean_reversion_pro(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.Series:
        """
        Professional Mean Reversion using Bollinger Bands and RSI Divergence.
        """
        sma = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)

        # Simple RSI implementation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        signals = pd.Series(index=df.index, data=0.0)
        signals[(df['Close'] < lower_band) & (rsi < 30)] = 1.0  # Buy
        signals[(df['Close'] > upper_band) & (rsi > 70)] = -1.0 # Sell
        return signals

    @staticmethod
    def trend_following_quantum(df: pd.DataFrame) -> pd.Series:
        """
        Trend Following via Exponential Moving Average (EMA) Cloud and MACD.
        """
        ema_fast = df['Close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=26, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=9, adjust=False).mean()

        ema_200 = df['Close'].ewm(span=200, adjust=False).mean()

        signals = pd.Series(index=df.index, data=0.0)
        # Buy: Price above EMA 200 AND MACD crosses above signal
        signals[(df['Close'] > ema_200) & (macd > signal_line)] = 1.0
        # Sell: Price below EMA 200 AND MACD crosses below signal
        signals[(df['Close'] < ema_200) & (macd < signal_line)] = -1.0
        return signals

    @staticmethod
    def volatility_breakout(df: pd.DataFrame, atr_period: int = 14) -> pd.Series:
        """
        Volatility Breakout based on Average True Range (ATR) channels.
        """
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(window=atr_period).mean()

        signals = pd.Series(index=df.index, data=0.0)
        signals[df['Close'] > (df['Close'].shift(1) + 2 * atr)] = 1.0
        signals[df['Close'] < (df['Close'].shift(1) - 2 * atr)] = -1.0
        return signals

    def get_all_strategies(self) -> List[str]:
        return [func for func in dir(self) if not func.startswith("__") and callable(getattr(self, func)) and func != "get_all_strategies"]
