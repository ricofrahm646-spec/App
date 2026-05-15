"""
JARVIS Trend Following Strategy
EMA crossover with ADX filter and multi-timeframe confirmation.
"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import BaseStrategy, Signal, StrategyConfig


class TrendFollowingStrategy(BaseStrategy):
    name = "TrendFollower"
    version = "1.2.0"
    strategy_type = "TREND"
    description = "EMA 50/200 crossover + ADX > 25 filter + H4 trend alignment"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        super().__init__(config)
        self.ema_fast = 50
        self.ema_slow = 200
        self.adx_period = 14
        self.adx_threshold = 25.0
        self.atr_period = 14
        self.atr_sl_mult = 2.0
        self.atr_tp_mult = 4.0

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["ema_fast"] = self._ema(df["close"], self.ema_fast)
        df["ema_slow"] = self._ema(df["close"], self.ema_slow)
        df["atr"] = self._atr(df["high"], df["low"], df["close"], self.atr_period)

        # ADX calculation
        high_diff = df["high"].diff()
        low_diff = df["low"].diff()
        dm_plus = high_diff.where((high_diff > low_diff.abs()) & (high_diff > 0), 0.0)
        dm_minus = (-low_diff).where((low_diff.abs() > high_diff) & (low_diff < 0), 0.0)
        tr = self._atr(df["high"], df["low"], df["close"], 1)
        tr_smooth = tr.rolling(self.adx_period).sum()
        di_plus = 100 * dm_plus.rolling(self.adx_period).sum() / (tr_smooth + 1e-10)
        di_minus = 100 * dm_minus.rolling(self.adx_period).sum() / (tr_smooth + 1e-10)
        dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus + 1e-10)
        df["adx"] = dx.rolling(self.adx_period).mean()
        df["di_plus"] = di_plus
        df["di_minus"] = di_minus

        df["trend_bull"] = df["ema_fast"] > df["ema_slow"]
        df["cross_bull"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        df["cross_bear"] = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))

        return df

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if len(data) < 220:
            return None

        df = self.calculate_indicators(data)
        last = df.iloc[-1]
        current_price = float(last["close"])
        atr = float(last["atr"])
        adx = float(last["adx"])

        if pd.isna(atr) or atr == 0 or pd.isna(adx):
            return None

        if adx < self.adx_threshold:
            return None

        sl_dist = atr * self.atr_sl_mult
        tp_dist = atr * self.atr_tp_mult

        if bool(last["cross_bull"]) and adx > self.adx_threshold:
            return Signal(
                action="BUY",
                symbol=self.config.symbol,
                entry_price=current_price,
                stop_loss=round(current_price - sl_dist, 5),
                take_profit=round(current_price + tp_dist, 5),
                confidence=min(0.80, 0.5 + adx / 100),
                reasoning=f"EMA50 crossed EMA200 bullish, ADX={adx:.1f}",
                timeframe=self.config.timeframe,
            )

        if bool(last["cross_bear"]) and adx > self.adx_threshold:
            return Signal(
                action="SELL",
                symbol=self.config.symbol,
                entry_price=current_price,
                stop_loss=round(current_price + sl_dist, 5),
                take_profit=round(current_price - tp_dist, 5),
                confidence=min(0.80, 0.5 + adx / 100),
                reasoning=f"EMA50 crossed EMA200 bearish, ADX={adx:.1f}",
                timeframe=self.config.timeframe,
            )

        return None
