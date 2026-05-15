from dataclasses import dataclass
from importlib import import_module
from typing import Any

from backend.app.models.schemas import OpenTrade, TradeRequest


@dataclass(frozen=True)
class MT5CommandPlan:
    action: str
    payload: dict[str, Any]
    requires_terminal: bool = True


class MT5Connector:
    """Thin adapter around the MetaTrader5 Python package.

    Cloud and Linux CI environments often do not have a local Windows MT5
    terminal. Methods therefore return command plans when the package or
    terminal is unavailable, keeping automation auditable and testable.
    """

    def __init__(self) -> None:
        try:
            self.mt5 = import_module("MetaTrader5")
        except ImportError:
            self.mt5 = None

    def available(self) -> bool:
        return self.mt5 is not None

    def open_order(self, request: TradeRequest, lot_size: float) -> MT5CommandPlan:
        return MT5CommandPlan(
            action="open_order",
            payload={
                "symbol": request.symbol,
                "side": request.side.value,
                "lot_size": lot_size,
                "entry_price": request.entry_price,
                "stop_loss": request.stop_loss,
                "take_profit": request.take_profit,
                "strategy_id": request.strategy_id,
            },
        )

    def close_order(self, trade: OpenTrade) -> MT5CommandPlan:
        return MT5CommandPlan(action="close_order", payload={"ticket": trade.ticket})

    def discover_charts(self) -> MT5CommandPlan:
        return MT5CommandPlan(
            action="discover_charts",
            payload={
                "description": "Read open chart symbols/timeframes from the connected MT5 terminal",
            },
        )

    def account_snapshot(self) -> MT5CommandPlan:
        return MT5CommandPlan(action="account_snapshot", payload={})
