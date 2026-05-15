"""
JARVIS Scalping Strategy
M5/M15 scalping using RSI + Stochastic + EMA confluence.
Designed for Gold (XAUUSD) and major Forex pairs.
"""

import numpy as np
import pandas as pd
from typing import Optional

from .base import BaseStrategy, Signal, StrategyConfig


class ScalpingStrategy(BaseStrategy):
    """
    High-frequency scalping strategy combining:
    - EMA trend filter (50 EMA on H1)
    - RSI for momentum (M5/M15)
    - Stochastic for entry timing
    - ATR for dynamic SL/TP
    """

    name = "GoldScalper"
    version = "2.1.0"
    strategy_type = "SCALPING"
    description = "M5 scalper with RSI + Stochastic signals, EMA trend filter, ATR-based SL/TP"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        super().__init__(config)
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.stoch_k = 5
        self.stoch_d = 3
        self.ema_fast = 9
        self.ema_slow = 21
        self.ema_trend = 50
        self.atr_period = 14
        self.atr_sl_mult = 1.5
        self.atr_tp_mult = 3.0

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["ema_fast"] = self._ema(df["close"], self.ema_fast)
        df["ema_slow"] = self._ema(df["close"], self.ema_slow)
        df["ema_trend"] = self._ema(df["close"], self.ema_trend)
        df["rsi"] = self._rsi(df["close"], self.rsi_period)
        df["atr"] = self._atr(df["high"], df["low"], df["close"], self.atr_period)

        # Stochastic
        low_min = df["low"].rolling(self.stoch_k).min()
        high_max = df["high"].rolling(self.stoch_k).max()
        df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-10)
        df["stoch_d"] = df["stoch_k"].rolling(self.stoch_d).mean()

        df["trend_up"] = df["close"] > df["ema_trend"]
        df["trend_down"] = df["close"] < df["ema_trend"]
        df["ema_cross_up"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        df["ema_cross_down"] = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))

        return df

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if len(data) < 60:
            return None

        df = self.calculate_indicators(data)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(last["rsi"]) or pd.isna(last["atr"]) or last["atr"] == 0:
            return None

        timestamp = df.index[-1]
        if not self.is_session_active(timestamp):
            return None

        current_price = float(last["close"])
        atr = float(last["atr"])
        sl_dist = atr * self.atr_sl_mult
        tp_dist = atr * self.atr_tp_mult

        # BUY conditions
        buy_conditions = [
            bool(last["trend_up"]),
            bool(last["ema_cross_up"]) or bool(prev["ema_cross_up"]),
            float(last["rsi"]) < self.rsi_overbought,
            float(last["rsi"]) > 40,
            float(last["stoch_k"]) < 80,
            float(last["stoch_k"]) > float(last["stoch_d"]),
        ]

        # SELL conditions
        sell_conditions = [
            bool(last["trend_down"]),
            bool(last["ema_cross_down"]) or bool(prev["ema_cross_down"]),
            float(last["rsi"]) > self.rsi_oversold,
            float(last["rsi"]) < 60,
            float(last["stoch_k"]) > 20,
            float(last["stoch_k"]) < float(last["stoch_d"]),
        ]

        buy_score = sum(buy_conditions) / len(buy_conditions)
        sell_score = sum(sell_conditions) / len(sell_conditions)

        if buy_score >= 0.7:
            return Signal(
                action="BUY",
                symbol=self.config.symbol,
                entry_price=current_price,
                stop_loss=round(current_price - sl_dist, 5),
                take_profit=round(current_price + tp_dist, 5),
                confidence=buy_score,
                reasoning=f"EMA cross up + RSI {last['rsi']:.1f} + Stoch {last['stoch_k']:.1f}",
                timeframe=self.config.timeframe,
            )

        if sell_score >= 0.7:
            return Signal(
                action="SELL",
                symbol=self.config.symbol,
                entry_price=current_price,
                stop_loss=round(current_price + sl_dist, 5),
                take_profit=round(current_price - tp_dist, 5),
                confidence=sell_score,
                reasoning=f"EMA cross down + RSI {last['rsi']:.1f} + Stoch {last['stoch_k']:.1f}",
                timeframe=self.config.timeframe,
            )

        return None
