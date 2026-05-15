"""Simplified ICT (Inner Circle Trader) strategy.

Trades the retracement into the 50%-equilibrium of the most recent swing leg
after a liquidity sweep, in the direction of the higher-timeframe bias (EMA200).
"""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("ict")
class ICTStrategy(Strategy):
    name = "ICT"

    @classmethod
    def default_parameters(cls) -> dict[str, int | float]:
        return {"swing_lookback": 20, "ema_bias": 200, "sweep_buffer": 0.0001}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.parameters
        n = int(p["swing_lookback"])
        bias = self.ema(df["close"], int(p["ema_bias"]))
        swing_high = df["high"].rolling(n, min_periods=1).max()
        swing_low = df["low"].rolling(n, min_periods=1).min()
        equilibrium = (swing_high + swing_low) / 2.0

        # liquidity sweep above swing high / below swing low
        sweep_up = (df["high"] > swing_high.shift()) & (df["close"] < swing_high.shift())
        sweep_dn = (df["low"] < swing_low.shift()) & (df["close"] > swing_low.shift())

        sig = pd.Series(0, index=df.index, dtype=int)
        sig[sweep_dn & (df["close"] > bias) & (df["close"] <= equilibrium)] = 1
        sig[sweep_up & (df["close"] < bias) & (df["close"] >= equilibrium)] = -1
        return sig
