"""Walk-forward analysis — slide a window through history and report per-fold metrics."""
from __future__ import annotations

import asyncio
from dataclasses import replace as _replace
from typing import Any

from backtesting.runner import BacktestConfig, _run


def _walk_forward(cfg: BacktestConfig, folds: int) -> dict[str, Any]:
    folds = max(folds, 2)
    bars_per_fold = max(cfg.bars // folds, 100)
    fold_metrics = []
    for i in range(folds):
        fold_cfg = _replace(cfg, bars=bars_per_fold, seed=(cfg.seed or 0) + i)
        result = _run(fold_cfg)
        fold_metrics.append({"fold": i + 1, **result["metrics"]})
    return {"folds": fold_metrics}


async def walk_forward(cfg: BacktestConfig, folds: int = 5) -> dict[str, Any]:
    return await asyncio.to_thread(_walk_forward, cfg, folds)
