"""Central risk controls for JARVIS execution paths."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CLOSE_EMERGENCY = "close_emergency"


@dataclass
class RiskContext:
    equity: float
    balance: float
    open_positions: list[dict[str, Any]]
    proposed_side: str  # "buy" | "sell"
    proposed_symbol: str


class RiskEngine:
    """
    Policy:
    - At most one concurrent position across the account (configurable).
    - No simultaneous buy and sell on the same symbol.
    - Emergency flatten if unrealized loss exceeds configured % of equity.
    """

    max_concurrent_positions: int = 1
    emergency_loss_pct_equity: float = 20.0

    def evaluate_new_order(self, ctx: RiskContext) -> tuple[RiskDecision, str]:
        if len(ctx.open_positions) >= self.max_concurrent_positions:
            return RiskDecision.BLOCK, "Max concurrent positions reached"

        same_symbol = [p for p in ctx.open_positions if p.get("symbol") == ctx.proposed_symbol]
        for p in same_symbol:
            if p.get("type") and p["type"].lower() != ctx.proposed_side.lower():
                return RiskDecision.BLOCK, "Opposite-side position already open on symbol"

        return RiskDecision.ALLOW, "OK"

    def evaluate_emergency(self, ctx: RiskContext) -> tuple[RiskDecision, str]:
        total_floating = sum(float(p.get("profit", 0) or 0) for p in ctx.open_positions)
        if ctx.equity <= 0:
            return RiskDecision.BLOCK, "Invalid equity"
        loss_ratio = (-total_floating / ctx.equity) * 100 if total_floating < 0 else 0.0
        if loss_ratio >= self.emergency_loss_pct_equity:
            return RiskDecision.CLOSE_EMERGENCY, f"Floating loss {loss_ratio:.2f}% of equity exceeds limit"
        return RiskDecision.ALLOW, "OK"
