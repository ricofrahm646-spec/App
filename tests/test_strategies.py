"""Smoke tests for strategy library + registry."""
from __future__ import annotations

import pandas as pd
import pytest

from strategies.registry import get_strategy, list_kinds


@pytest.fixture(scope="module")
def ohlcv() -> pd.DataFrame:
    from backtesting.data import load_history

    return load_history("EURUSD", "M15", bars=400, seed=42)


def test_registry_lists_all_kinds():
    kinds = list_kinds()
    expected = {
        "trend_following",
        "scalping",
        "ict",
        "smart_money",
        "mean_reversion",
        "breakout",
        "momentum",
        "session_trading",
    }
    assert expected.issubset(set(kinds))


@pytest.mark.parametrize("kind", list_kinds())
def test_strategies_produce_signals(kind: str, ohlcv: pd.DataFrame):
    strat = get_strategy(kind)
    sig = strat.signals(ohlcv)
    assert len(sig) == len(ohlcv)
    assert set(sig.unique()).issubset({-1, 0, 1})
