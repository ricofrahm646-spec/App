"""Risk management for trading simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RiskAssessment:
    """Result describing position sizing and safety status."""

    allowed: bool
    position_size: float
    risk_amount: float
    reason: str
    metadata: dict[str, Any]


class RiskManager:
    """Handles position sizing, max risk, and kill switch logic."""

    def __init__(
        self,
        *,
        max_risk_per_trade: float = 0.02,
        max_drawdown_limit: float = 0.18,
        max_consecutive_losses: int = 8,
    ) -> None:
        self.max_risk_per_trade = max_risk_per_trade
        self.max_drawdown_limit = max_drawdown_limit
        self.max_consecutive_losses = max_consecutive_losses

    def assess_trade(
        self,
        *,
        equity: float,
        entry_price: float,
        stop_price: float,
        current_drawdown: float,
        consecutive_losses: int,
    ) -> RiskAssessment:
        if current_drawdown >= self.max_drawdown_limit:
            return RiskAssessment(
                allowed=False,
                position_size=0.0,
                risk_amount=0.0,
                reason="Kill switch active: max drawdown exceeded.",
                metadata={"drawdown": current_drawdown},
            )
        if consecutive_losses >= self.max_consecutive_losses:
            return RiskAssessment(
                allowed=False,
                position_size=0.0,
                risk_amount=0.0,
                reason="Kill switch active: too many consecutive losses.",
                metadata={"consecutive_losses": consecutive_losses},
            )

        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return RiskAssessment(
                allowed=False,
                position_size=0.0,
                risk_amount=0.0,
                reason="Invalid stop distance; cannot compute position size.",
                metadata={"entry_price": entry_price, "stop_price": stop_price},
            )

        risk_amount = equity * self.max_risk_per_trade
        position_size = risk_amount / risk_per_unit
        return RiskAssessment(
            allowed=True,
            position_size=position_size,
            risk_amount=risk_amount,
            reason="Trade allowed under risk limits.",
            metadata={"risk_per_unit": risk_per_unit},
        )

