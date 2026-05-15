from datetime import datetime

from app.models.schemas import TradeRequest, TradeState


class MT5Connector:
    """
    MT5 integration facade.
    This foundation uses an in-memory state and is designed
    to be replaced by real MetaTrader 5 bridge calls.
    """

    def __init__(self) -> None:
        self._trade_state = TradeState(is_open=False)
        self._active_symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
        self._active_timeframes = ["M5", "M15", "H1"]

    def get_trade_state(self) -> TradeState:
        return self._trade_state

    def get_active_context(self) -> dict[str, list[str]]:
        return {
            "symbols": self._active_symbols,
            "timeframes": self._active_timeframes,
        }

    def open_trade(self, request: TradeRequest, entry_price: float) -> TradeState:
        self._trade_state = TradeState(
            is_open=True,
            symbol=request.symbol,
            side=request.side,
            entry_price=entry_price,
            unrealized_pnl_pct=0.0,
            opened_at=datetime.utcnow(),
        )
        return self._trade_state

    def close_trade(self) -> TradeState:
        self._trade_state = TradeState(is_open=False)
        return self._trade_state

    def update_unrealized_pnl(self, pnl_pct: float) -> TradeState:
        if not self._trade_state.is_open:
            return self._trade_state
        self._trade_state.unrealized_pnl_pct = pnl_pct
        return self._trade_state
