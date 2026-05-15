"""Base class shared by every JARVIS strategy."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Signal:
    timestamp: pd.Timestamp
    side: str  # BUY / SELL / FLAT
    strength: float = 1.0
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


class Strategy(ABC):
    """Abstract strategy interface.

    A strategy consumes an OHLCV DataFrame indexed by datetime and produces:
    * `signals(df)`  → an integer Series in {-1, 0, +1}
    * `latest_signal(df)` → a `Signal` instance for live trading
    """

    name: str = "base"
    kind: str = "base"

    def __init__(self, **parameters: Any) -> None:
        self.parameters: dict[str, Any] = {**self.default_parameters(), **parameters}

    @classmethod
    def default_parameters(cls) -> dict[str, Any]:
        return {}

    @abstractmethod
    def signals(self, df: pd.DataFrame) -> pd.Series: ...

    def latest_signal(self, df: pd.DataFrame) -> Signal:
        sig = self.signals(df)
        if len(sig) == 0:
            return Signal(timestamp=pd.Timestamp.utcnow(), side="FLAT")
        last = int(sig.iloc[-1])
        side = "BUY" if last > 0 else "SELL" if last < 0 else "FLAT"
        return Signal(
            timestamp=df.index[-1],
            side=side,
            strength=abs(float(sig.iloc[-1])),
            reason=f"{self.name} ({self.kind})",
        )

    # ── helpers ─────────────────────────────────────────────────
    @staticmethod
    def ema(series: pd.Series, length: int) -> pd.Series:
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, length: int) -> pd.Series:
        return series.rolling(length, min_periods=1).mean()

    @staticmethod
    def rsi(series: pd.Series, length: int = 14) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0).rolling(length, min_periods=length).mean()
        down = -delta.clip(upper=0).rolling(length, min_periods=length).mean()
        rs = up / down.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(length, min_periods=1).mean()
