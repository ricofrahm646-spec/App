"""Backtesting facade — wire VectorBT / Backtrader in research workflows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str
    start: str
    end: str


class BacktestEngine:
    def run_vectorbt_stub(self, req: BacktestRequest) -> dict[str, Any]:
        """Placeholder metrics — replace with real VectorBT pipeline."""
        return {
            "engine": "vectorbt_stub",
            "request": req.model_dump(),
            "metrics": {
                "total_return": None,
                "sharpe": None,
                "max_drawdown": None,
                "winrate": None,
                "trades": None,
            },
            "note": "Install optional stack from backend/requirements-ai.txt for full runs.",
        }
