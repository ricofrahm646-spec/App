from math import floor

from backend.app.models.schemas import AccountState, OpenTrade, RiskDecision, TradeRequest


class RiskEngine:
    def __init__(self, max_open_trades: int = 1, emergency_loss_percent: float = 20.0) -> None:
        self.max_open_trades = max_open_trades
        self.emergency_loss_percent = emergency_loss_percent

    def evaluate_trade(
        self,
        account: AccountState,
        request: TradeRequest,
        open_trades: list[OpenTrade],
    ) -> RiskDecision:
        if len(open_trades) >= self.max_open_trades or account.open_trades >= self.max_open_trades:
            return RiskDecision(
                allowed=False,
                reason="Maximum one open trade is allowed",
                actions=["reject_order"],
            )

        if any(trade.symbol == request.symbol and trade.side != request.side for trade in open_trades):
            return RiskDecision(
                allowed=False,
                reason="Hedged buy/sell exposure is forbidden",
                actions=["reject_order"],
            )

        stop_distance = abs(request.entry_price - request.stop_loss)
        if stop_distance <= 0:
            return RiskDecision(
                allowed=False,
                reason="Stop loss must be different from entry price",
                actions=["reject_order"],
            )

        lot_size = self.calculate_lot_size(account.equity, request.risk_percent, stop_distance)
        if lot_size <= 0:
            return RiskDecision(
                allowed=False,
                reason="Calculated lot size is too small for execution",
                actions=["reject_order"],
            )

        return RiskDecision(
            allowed=True,
            reason="Risk checks passed",
            lot_size=lot_size,
            actions=["submit_order", "attach_stop_loss", "attach_take_profit"],
        )

    def monitor_open_trade(self, account: AccountState, trade: OpenTrade) -> RiskDecision:
        loss_percent = abs(min(0.0, trade.floating_pl)) / account.balance * 100
        if loss_percent >= self.emergency_loss_percent:
            return RiskDecision(
                allowed=False,
                reason=f"Emergency loss threshold reached: {loss_percent:.2f}%",
                emergency_close=True,
                actions=["close_trade", "disable_strategy", "notify_risk"],
            )
        return RiskDecision(allowed=True, reason="Open trade within risk policy")

    @staticmethod
    def calculate_lot_size(equity: float, risk_percent: float, stop_distance: float) -> float:
        risk_amount = equity * (risk_percent / 100)
        raw_lot = risk_amount / (stop_distance * 100_000)
        return max(0.01, floor(raw_lot * 100) / 100)
