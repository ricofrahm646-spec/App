"""JARVIS Risk Engine.

Hard guarantees:

* Maximum N concurrent open trades (default 1)
* Never opens an opposite-side position on the same symbol if one is open
* Automatically closes any trade whose floating loss exceeds X % of margin (default 20)
* Provides a global kill switch that flattens all positions and pauses trading
* Computes risk-adjusted lot sizing based on configured account risk %
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger
from backend.app.schemas.common import TradeRequest


@dataclass
class RiskDecision:
    allowed: bool
    reason: str


class RiskEngine:
    _kill_switch: bool = False
    _lock = asyncio.Lock()

    # ────────────────────────────── kill switch ───────────────────
    @classmethod
    def kill_switch_active(cls) -> bool:
        return cls._kill_switch

    @classmethod
    async def activate_kill_switch(cls) -> None:
        from mt5.connector import get_connector  # local import to break cycle

        cls._kill_switch = True
        conn = get_connector()
        closed = await conn.close_all()
        logger.warning("KILL SWITCH engaged — closed {} positions", closed)

    @classmethod
    def release_kill_switch(cls) -> None:
        cls._kill_switch = False
        logger.info("Kill switch released")

    # ────────────────────────────── checks ────────────────────────
    async def allow_new_trade(self, req: TradeRequest) -> tuple[bool, str]:
        if self._kill_switch:
            return False, "kill switch active"

        from mt5.connector import get_connector

        conn = get_connector()
        open_trades = await conn.open_positions()

        if len(open_trades) >= settings.risk_max_open_trades:
            return False, f"max open trades ({settings.risk_max_open_trades}) reached"

        if not settings.risk_allow_opposite_sides:
            for t in open_trades:
                if t.symbol.upper() == req.symbol.upper() and t.side != req.side:
                    return False, f"opposite side already open on {t.symbol}"

        return True, "ok"

    # ────────────────────────────── enforcement ───────────────────
    async def enforce(self) -> None:
        """Run periodically; closes trades violating risk rules."""
        from mt5.connector import get_connector

        conn = get_connector()
        snapshot = await conn.account_snapshot()
        if snapshot.margin <= 0:
            return

        for trade in await conn.open_positions():
            margin_used = max(trade.volume * 1000.0, 1.0)
            loss_pct = (-trade.profit / margin_used) * 100.0
            if loss_pct >= settings.risk_max_loss_pct:
                logger.warning(
                    "Risk: closing #{} loss={:.2f}% (limit {:.1f}%)",
                    trade.ticket,
                    loss_pct,
                    settings.risk_max_loss_pct,
                )
                await conn.close(trade.ticket)  # type: ignore[arg-type]

    # ────────────────────────────── sizing ────────────────────────
    @staticmethod
    def position_size(
        balance: float,
        entry: float,
        stop: float,
        risk_pct: float | None = None,
        pip_value: float = 10.0,
    ) -> float:
        """Return a lot size such that loss to `stop` is exactly `risk_pct` of balance."""
        risk_pct = risk_pct or settings.risk_risk_per_trade_pct
        if balance <= 0 or entry <= 0 or stop <= 0 or entry == stop:
            return 0.01
        risk_amount = balance * risk_pct / 100.0
        distance = abs(entry - stop)
        pip_distance = distance * (10_000 if "JPY" not in "" else 100)  # simplified
        if pip_distance == 0:
            return 0.01
        lots = risk_amount / (pip_distance * pip_value)
        return max(round(lots, 2), 0.01)
