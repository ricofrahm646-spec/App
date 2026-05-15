"""Smart Money Concepts — Orderblock + Break of Structure (simplified)."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("smart_money")
class SmartMoneyStrategy(Strategy):
    name = "Smart Money"

    @classmethod
    def default_parameters(cls) -> dict[str, int]:
        return {"structure_lookback": 30, "ob_size": 3}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.parameters
        n = int(p["structure_lookback"])
        prior_high = df["high"].rolling(n, min_periods=1).max().shift(1)
        prior_low = df["low"].rolling(n, min_periods=1).min().shift(1)
        bos_up = df["close"] > prior_high
        bos_dn = df["close"] < prior_low
        body = (df["close"] - df["open"]).abs()
        large_body = body > body.rolling(20, min_periods=1).mean() * 1.5
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[bos_up & large_body] = 1
        sig[bos_dn & large_body] = -1
        return sig
