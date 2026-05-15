"""Session breakout — trade the London open range, exit at NY close."""
from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register("session_trading")
class SessionTradingStrategy(Strategy):
    name = "Session Trader"

    @classmethod
    def default_parameters(cls) -> dict[str, int]:
        return {"session_start_h": 7, "session_end_h": 16}

    def signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.parameters
        hours = df.index.hour if hasattr(df.index, "hour") else pd.to_datetime(df.index).hour
        sig = pd.Series(0, index=df.index, dtype=int)
        in_session = (hours >= int(p["session_start_h"])) & (hours <= int(p["session_end_h"]))
        ema_fast = self.ema(df["close"], 8)
        ema_slow = self.ema(df["close"], 21)
        sig[(ema_fast > ema_slow) & in_session] = 1
        sig[(ema_fast < ema_slow) & in_session] = -1
        return sig
