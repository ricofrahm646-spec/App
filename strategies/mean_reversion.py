"""Bollinger-band mean reversion."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("mean_reversion")
class MeanReversionStrategy(Strategy):
    name = "Mean Reversion"

    @classmethod
    def default_parameters(cls) -> dict[str, int | float]:
        return {"length": 20, "stdev": 2.0}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.parameters
        ma = self.sma(df["close"], int(p["length"]))
        sd = df["close"].rolling(int(p["length"]), min_periods=1).std().fillna(0)
        upper = ma + float(p["stdev"]) * sd
        lower = ma - float(p["stdev"]) * sd
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[df["close"] < lower] = 1
        sig[df["close"] > upper] = -1
        return sig
