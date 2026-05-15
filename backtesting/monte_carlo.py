"""Monte Carlo robustness analysis: resample trade returns with replacement."""
from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from backtesting.runner import BacktestConfig, _run


def _monte_carlo(cfg: BacktestConfig, simulations: int) -> dict[str, Any]:
    base = _run(cfg)
    eq = np.array(base["equity_curve"])
    if len(eq) < 2:
        return {"base": base, "simulations": []}
    returns = np.diff(eq) / eq[:-1]
    rng = np.random.default_rng(cfg.seed)
    finals = []
    drawdowns = []
    for _ in range(simulations):
        sample = rng.choice(returns, size=len(returns), replace=True)
        curve = (1 + sample).cumprod() * cfg.initial_balance
        finals.append(float(curve[-1]))
        dd = float((curve / np.maximum.accumulate(curve) - 1).min() * 100.0)
        drawdowns.append(dd)
    return {
        "base_metrics": base["metrics"],
        "monte_carlo": {
            "simulations": simulations,
            "final_balance_p05": float(np.percentile(finals, 5)),
            "final_balance_p50": float(np.percentile(finals, 50)),
            "final_balance_p95": float(np.percentile(finals, 95)),
            "max_drawdown_p05_pct": float(np.percentile(drawdowns, 5)),
            "max_drawdown_p95_pct": float(np.percentile(drawdowns, 95)),
        },
    }


async def monte_carlo(cfg: BacktestConfig, simulations: int = 500) -> dict[str, Any]:
    return await asyncio.to_thread(_monte_carlo, cfg, simulations)
