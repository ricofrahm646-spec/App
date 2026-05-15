"""Vectorised backtesting runner with slippage + spread simulation.

The engine is deliberately framework-agnostic: it consumes signals from any
strategy in `strategies.registry` and produces a metrics dict + equity curve.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from backtesting.data import load_history
from strategies.registry import get_strategy


@dataclass
class BacktestConfig:
    strategy: str
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    bars: int = 5000
    parameters: dict[str, Any] = field(default_factory=dict)
    spread_pips: float = 0.5
    slippage_pips: float = 0.2
    initial_balance: float = 10_000.0
    risk_per_trade: float = 0.01
    seed: int | None = None


def _pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def _run(cfg: BacktestConfig) -> dict[str, Any]:
    df = load_history(cfg.symbol, cfg.timeframe, cfg.bars, seed=cfg.seed)
    strat = get_strategy(cfg.strategy, **cfg.parameters)
    signals = strat.signals(df).reindex(df.index).fillna(0).astype(int)

    position = signals.shift(1).fillna(0).astype(int)
    raw_returns = df["close"].pct_change().fillna(0)

    pip = _pip_size(cfg.symbol)
    fee_pct = ((cfg.spread_pips + cfg.slippage_pips) * pip) / df["close"]
    trades_occurred = position.diff().abs().fillna(0).astype(int)
    strat_returns = position * raw_returns - trades_occurred * fee_pct
    equity = (1 + strat_returns).cumprod() * cfg.initial_balance

    total_trades = int(trades_occurred.sum())
    pos_returns = strat_returns[strat_returns > 0]
    neg_returns = strat_returns[strat_returns < 0]
    winrate = float(len(pos_returns) / max(len(pos_returns) + len(neg_returns), 1)) * 100.0
    profit_factor = (
        float(pos_returns.sum() / abs(neg_returns.sum())) if neg_returns.sum() != 0 else 0.0
    )
    drawdown = float((equity / equity.cummax() - 1).min() * 100.0)
    sharpe = (
        float(strat_returns.mean() / strat_returns.std() * np.sqrt(252 * 24))
        if strat_returns.std() > 0
        else 0.0
    )
    final_balance = float(equity.iloc[-1])

    return {
        "config": {
            "strategy": cfg.strategy,
            "symbol": cfg.symbol,
            "timeframe": cfg.timeframe,
            "bars": cfg.bars,
            "parameters": cfg.parameters,
        },
        "metrics": {
            "trades": total_trades,
            "winrate_pct": round(winrate, 2),
            "profit_factor": round(profit_factor, 3),
            "max_drawdown_pct": round(drawdown, 2),
            "sharpe": round(sharpe, 3),
            "final_balance": round(final_balance, 2),
            "return_pct": round((final_balance / cfg.initial_balance - 1) * 100.0, 2),
        },
        "equity_curve": equity.round(4).tolist(),
        "timestamps": [t.isoformat() for t in df.index],
    }


async def run_backtest(cfg: BacktestConfig) -> dict[str, Any]:
    return await asyncio.to_thread(_run, cfg)
