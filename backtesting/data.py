"""Lightweight synthetic OHLCV generator + CSV/Parquet loader.

When historical data is not available locally the generator produces a
geometric-brownian-motion OHLCV series so the rest of the platform always has
something to backtest against. Replace `load_history` with your real data
provider when you have one.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.core.config import settings


_TIMEFRAMES = {
    "M1": pd.Timedelta(minutes=1),
    "M5": pd.Timedelta(minutes=5),
    "M15": pd.Timedelta(minutes=15),
    "M30": pd.Timedelta(minutes=30),
    "H1": pd.Timedelta(hours=1),
    "H4": pd.Timedelta(hours=4),
    "D1": pd.Timedelta(days=1),
}


def _data_root() -> Path:
    return settings.project_root / "data"


def load_history(
    symbol: str,
    timeframe: str = "M15",
    bars: int = 5000,
    seed: int | None = None,
) -> pd.DataFrame:
    """Load OHLCV history. Falls back to a synthetic series if no file is found."""
    csv_path = _data_root() / f"{symbol.upper()}_{timeframe.upper()}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["time"])
        df = df.set_index("time").tail(bars)
        return df

    return _synthetic(symbol=symbol, timeframe=timeframe, bars=bars, seed=seed)


def _synthetic(symbol: str, timeframe: str, bars: int, seed: int | None) -> pd.DataFrame:
    rng = np.random.default_rng(seed if seed is not None else abs(hash(symbol)) % 2**32)
    start_price = {
        "EURUSD": 1.085, "GBPUSD": 1.265, "USDJPY": 156.3, "XAUUSD": 2350.0, "BTCUSD": 65000.0,
    }.get(symbol.upper(), 1.0)
    step = _TIMEFRAMES.get(timeframe.upper(), pd.Timedelta(minutes=15))
    end = pd.Timestamp.now(tz="UTC").tz_convert(None).floor("min")
    idx = pd.date_range(end=end, periods=bars, freq=step)
    vol = 0.0008 if "USD" in symbol[:6] and symbol.upper() != "BTCUSD" else 0.01
    shocks = rng.normal(0, vol, size=bars)
    close = start_price * np.exp(np.cumsum(shocks))
    open_ = np.concatenate([[start_price], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 2, bars)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 2, bars)))
    volume = rng.integers(100, 1000, size=bars).astype(float)
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx
    )
    df.index.name = "time"
    return df
