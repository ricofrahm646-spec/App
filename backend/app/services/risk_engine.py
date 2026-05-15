from dataclasses import dataclass


@dataclass(slots=True)
class TradeState:
    side: str | None
    live_trades: int
    unrealized_loss_percent: float


@dataclass(slots=True)
class RiskDecision:
    allow_entry: bool
    should_force_close: bool
    reason: str


class RiskEngine:
    """Safe-by-default controls for JARVIS live trading."""

    max_live_trades: int = 1
    allow_hedging: bool = False
    force_close_loss_percent: float = 20.0

    def evaluate_entry(self, existing_side: str | None, requested_side: str) -> RiskDecision:
        requested_side = requested_side.lower()
        existing = existing_side.lower() if existing_side else None

        if requested_side not in {"buy", "sell"}:
            return RiskDecision(False, False, "Only buy and sell directions are supported.")

        if existing and existing != requested_side and not self.allow_hedging:
            return RiskDecision(False, False, "Simultaneous buy and sell exposure is disabled.")

        if existing == requested_side:
            return RiskDecision(False, False, "Only one live trade is allowed at a time.")

        return RiskDecision(True, False, "Entry is allowed by current guardrails.")

    def evaluate_live_state(self, state: TradeState) -> RiskDecision:
        if state.live_trades > self.max_live_trades:
            return RiskDecision(False, True, "Too many live trades detected; reduce exposure immediately.")

        if state.unrealized_loss_percent >= self.force_close_loss_percent:
            return RiskDecision(False, True, "Loss threshold breached; force-close the trade.")

        return RiskDecision(True, False, "Live trade remains within configured limits.")
