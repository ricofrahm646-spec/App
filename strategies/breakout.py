"""Donchian breakout strategy."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("breakout")
class BreakoutStrategy(Strategy):
    name = "Breakout"

    @classmethod
    def default_parameters(cls) -> dict[str, int]:
        return {"length": 20}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        n = int(self.parameters["length"])
        upper = df["high"].rolling(n, min_periods=1).max().shift(1)
        lower = df["low"].rolling(n, min_periods=1).min().shift(1)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[df["close"] > upper] = 1
        sig[df["close"] < lower] = -1
        return sig
