from app.models.trading import RiskSnapshot, TradePosition, TradeRequest


class RiskEngineError(Exception):
    pass


class RiskEngine:
    """
    Enforces hard constraints:
    - only one open trade at a time
    - no simultaneous buy and sell exposure
    - emergency close when loss >= 20%
    """

    def validate_new_trade(self, request: TradeRequest, open_positions: list[TradePosition]) -> None:
        if len(open_positions) >= 1:
            raise RiskEngineError("Maximal ein Trade gleichzeitig erlaubt.")

        if any(position.side != request.side for position in open_positions):
            raise RiskEngineError("Gleichzeitiges Buy/Sell ist nicht erlaubt.")

    def detect_emergency_close(self, position: TradePosition) -> bool:
        return position.pnl_percent <= -20.0

    def summarize_account(self, equity: float, margin: float, peak_equity: float) -> RiskSnapshot:
        drawdown = 0.0
        if peak_equity > 0:
            drawdown = ((peak_equity - equity) / peak_equity) * 100
        return RiskSnapshot(equity=equity, margin=margin, drawdown_percent=max(drawdown, 0.0))
