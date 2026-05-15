"""
JARVIS Mean Reversion Strategy
Bollinger Bands + RSI oversold/overbought for counter-trend entries.
"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import BaseStrategy, Signal, StrategyConfig


class MeanReversionStrategy(BaseStrategy):
    name = "MeanReversion"
    version = "1.1.0"
    strategy_type = "MEAN_REVERSION"
    description = "Bollinger Bands extremes + RSI confirmation, exits at BB midline"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        super().__init__(config)
        self.bb_period = 20
        self.bb_std = 2.0
        self.rsi_period = 14
        self.rsi_buy_threshold = 30
        self.rsi_sell_threshold = 70
        self.atr_period = 14

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["bb_upper"], df["bb_mid"], df["bb_lower"] = self._bollinger(df["close"], self.bb_period, self.bb_std)
        df["rsi"] = self._rsi(df["close"], self.rsi_period)
        df["atr"] = self._atr(df["high"], df["low"], df["close"], self.atr_period)
        df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
        return df

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if len(data) < 30:
            return None

        df = self.calculate_indicators(data)
        last = df.iloc[-1]
        current_price = float(last["close"])
        atr = float(last["atr"])

        if pd.isna(atr) or atr == 0:
            return None

        rsi = float(last["rsi"])
        bb_pct = float(last["bb_pct"])

        # BUY: price at lower band + RSI oversold
        if bb_pct < 0.05 and rsi < self.rsi_buy_threshold:
            return Signal(
                action="BUY",
                symbol=self.config.symbol,
                entry_price=current_price,
                stop_loss=round(float(last["bb_lower"]) - atr * 0.5, 5),
                take_profit=round(float(last["bb_mid"]), 5),
                confidence=min(0.75, (self.rsi_buy_threshold - rsi) / self.rsi_buy_threshold + 0.5),
                reasoning=f"BB lower band + RSI oversold ({rsi:.1f})",
                timeframe=self.config.timeframe,
            )

        # SELL: price at upper band + RSI overbought
        if bb_pct > 0.95 and rsi > self.rsi_sell_threshold:
            return Signal(
                action="SELL",
                symbol=self.config.symbol,
                entry_price=current_price,
                stop_loss=round(float(last["bb_upper"]) + atr * 0.5, 5),
                take_profit=round(float(last["bb_mid"]), 5),
                confidence=min(0.75, (rsi - self.rsi_sell_threshold) / (100 - self.rsi_sell_threshold) + 0.5),
                reasoning=f"BB upper band + RSI overbought ({rsi:.1f})",
                timeframe=self.config.timeframe,
            )

        return None
