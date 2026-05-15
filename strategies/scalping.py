"""Fast EMA scalping strategy with RSI filter — typically applied to M1/M5."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("scalping")
class ScalpingStrategy(Strategy):
    name = "Scalper"

    @classmethod
    def default_parameters(cls) -> dict[str, int | float]:
        return {"fast": 5, "slow": 13, "rsi_length": 7, "rsi_buy": 55.0, "rsi_sell": 45.0}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.parameters
        fast = self.ema(df["close"], int(p["fast"]))
        slow = self.ema(df["close"], int(p["slow"]))
        rsi = self.rsi(df["close"], int(p["rsi_length"]))
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[(fast > slow) & (rsi > p["rsi_buy"])] = 1
        sig[(fast < slow) & (rsi < p["rsi_sell"])] = -1
        return sig
