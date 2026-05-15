"""Backtesting engine smoke tests."""
from __future__ import annotations

import asyncio

import pytest

from backtesting.runner import BacktestConfig, run_backtest


@pytest.mark.parametrize("strategy", ["trend_following", "scalping", "breakout"])
def test_backtest_runs(strategy: str):
    cfg = BacktestConfig(strategy=strategy, bars=500, seed=7)
    result = asyncio.run(run_backtest(cfg))
    assert "metrics" in result
    assert "equity_curve" in result
    assert result["metrics"]["trades"] >= 0
    assert len(result["equity_curve"]) == 500
