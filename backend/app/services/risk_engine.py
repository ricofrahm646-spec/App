from dataclasses import dataclass

from app.models.schemas import RiskDecision, TradeRequest, TradeState


@dataclass
class AccountSnapshot:
    balance: float
    equity: float
    margin_level: float


class RiskEngine:
    """Centralized risk constraints for all trading actions."""

    def __init__(self, max_loss_threshold_pct: float = 20.0) -> None:
        self.max_loss_threshold_pct = max_loss_threshold_pct

    def evaluate_open_trade(
        self,
        trade_request: TradeRequest,
        current_state: TradeState,
        account: AccountSnapshot,
    ) -> RiskDecision:
        if current_state.is_open:
            return RiskDecision(
                approved=False,
                reason="Only one concurrent trade is allowed.",
                max_loss_threshold_pct=self.max_loss_threshold_pct,
            )

        if trade_request.risk_percent > 2.0:
            return RiskDecision(
                approved=False,
                reason="Risk percent exceeds hard cap of 2%.",
                max_loss_threshold_pct=self.max_loss_threshold_pct,
            )

        if account.margin_level < 100:
            return RiskDecision(
                approved=False,
                reason="Margin level too low for a new position.",
                max_loss_threshold_pct=self.max_loss_threshold_pct,
            )

        return RiskDecision(
            approved=True,
            reason="Trade approved by risk policy.",
            max_loss_threshold_pct=self.max_loss_threshold_pct,
        )

    def should_force_close(self, current_state: TradeState) -> bool:
        return current_state.is_open and current_state.unrealized_pnl_pct <= -self.max_loss_threshold_pct
