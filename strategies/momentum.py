"""Rate-of-change momentum."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("momentum")
class MomentumStrategy(Strategy):
    name = "Momentum"

    @classmethod
    def default_parameters(cls) -> dict[str, int | float]:
        return {"length": 14, "threshold": 0.0015}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.parameters
        roc = df["close"].pct_change(int(p["length"]))
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[roc > float(p["threshold"])] = 1
        sig[roc < -float(p["threshold"])] = -1
        return sig
