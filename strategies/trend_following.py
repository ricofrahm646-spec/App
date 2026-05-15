"""EMA-cross trend follower with ATR confirmation."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("trend_following")
class TrendFollowingStrategy(Strategy):
    name = "Trend Follower"

    @classmethod
    def default_parameters(cls) -> dict[str, int]:
        return {"fast": 20, "slow": 50, "atr_length": 14, "atr_mult": 0.0}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        fast = self.ema(df["close"], self.parameters["fast"])
        slow = self.ema(df["close"], self.parameters["slow"])
        atr = self.atr(df, self.parameters["atr_length"])
        threshold = atr * self.parameters["atr_mult"]
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[fast > slow + threshold] = 1
        sig[fast < slow - threshold] = -1
        return sig
