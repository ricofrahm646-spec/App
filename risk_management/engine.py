from dataclasses import dataclass
from enum import Enum
from math import floor


class RiskDecision(str, Enum):
    allow = "allow"
    reject = "reject"
    force_close = "force_close"


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str
    volume: float
    entry_price: float
    current_price: float
    unrealized_loss_percent: float = 0.0


@dataclass(frozen=True)
class RiskCheck:
    decision: RiskDecision
    reason: str
    lot_size: float = 0.0


class RiskEngine:
    """Centralizes hard trading invariants used by live and paper adapters."""

    def __init__(
        self,
        *,
        max_open_trades: int = 1,
        forced_close_loss_percent: float = 20.0,
        min_lot: float = 0.01,
        lot_step: float = 0.01,
    ) -> None:
        self.max_open_trades = max_open_trades
        self.forced_close_loss_percent = forced_close_loss_percent
        self.min_lot = min_lot
        self.lot_step = lot_step

    def evaluate_existing_positions(self, positions: list[Position]) -> RiskCheck:
        for position in positions:
            if position.unrealized_loss_percent >= self.forced_close_loss_percent:
                return RiskCheck(
                    decision=RiskDecision.force_close,
                    reason=(
                        f"{position.symbol} exceeds allowed loss "
                        f"({position.unrealized_loss_percent:.2f}%)."
                    ),
                )

        if len(positions) > self.max_open_trades:
            return RiskCheck(
                decision=RiskDecision.reject,
                reason=f"More than {self.max_open_trades} open trade detected.",
            )

        if self._has_hedged_exposure(positions):
            return RiskCheck(
                decision=RiskDecision.reject,
                reason="Simultaneous buy and sell exposure is not allowed.",
            )

        return RiskCheck(decision=RiskDecision.allow, reason="Risk state is healthy.")

    def validate_new_trade(
        self,
        *,
        symbol: str,
        side: str,
        balance: float,
        risk_percent: float,
        stop_loss_points: float,
        point_value: float,
        open_positions: list[Position],
    ) -> RiskCheck:
        current_state = self.evaluate_existing_positions(open_positions)
        if current_state.decision != RiskDecision.allow:
            return current_state

        if len(open_positions) >= self.max_open_trades:
            return RiskCheck(
                decision=RiskDecision.reject,
                reason=f"Max {self.max_open_trades} open trade is allowed.",
            )

        for position in open_positions:
            if position.symbol == symbol and position.side.lower() != side.lower():
                return RiskCheck(
                    decision=RiskDecision.reject,
                    reason="Opposite exposure on the same symbol is blocked.",
                )

        lot_size = self.calculate_lot_size(
            balance=balance,
            risk_percent=risk_percent,
            stop_loss_points=stop_loss_points,
            point_value=point_value,
        )
        if lot_size < self.min_lot:
            return RiskCheck(
                decision=RiskDecision.reject,
                reason="Calculated lot size is below broker minimum.",
            )

        return RiskCheck(
            decision=RiskDecision.allow,
            reason="Trade passed JARVIS risk rules.",
            lot_size=lot_size,
        )

    def calculate_lot_size(
        self,
        *,
        balance: float,
        risk_percent: float,
        stop_loss_points: float,
        point_value: float,
    ) -> float:
        if balance <= 0 or risk_percent <= 0 or stop_loss_points <= 0 or point_value <= 0:
            return 0.0

        risk_amount = balance * (risk_percent / 100)
        raw_lots = risk_amount / (stop_loss_points * point_value)
        stepped = floor(raw_lots / self.lot_step) * self.lot_step
        return round(max(stepped, 0.0), 2)

    @staticmethod
    def _has_hedged_exposure(positions: list[Position]) -> bool:
        sides = {position.side.lower() for position in positions}
        return "buy" in sides and "sell" in sides
