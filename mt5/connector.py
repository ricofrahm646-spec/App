from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.app.config import Settings
from risk_management.engine import Position, RiskDecision, RiskEngine


@dataclass
class MT5Account:
    balance: float = 10_000.0
    equity: float = 10_000.0
    margin: float = 0.0
    free_margin: float = 10_000.0
    currency: str = "USD"


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: str
    volume: float
    stop_loss_points: float
    take_profit_points: float
    opened_at: datetime = field(default_factory=datetime.utcnow)


class MT5Connector:
    """Safe MT5 adapter with paper-mode fallback and hard risk enforcement."""

    def __init__(self, settings: Settings, risk_engine: RiskEngine) -> None:
        self.settings = settings
        self.risk_engine = risk_engine
        self._paper_orders: list[PaperOrder] = []
        self._mt5 = self._load_mt5()

    @property
    def is_live_ready(self) -> bool:
        return bool(self._mt5 and self.settings.live_trading_enabled)

    def initialize(self) -> dict[str, Any]:
        if not self._mt5:
            return {"connected": False, "mode": "paper", "reason": "MetaTrader5 package unavailable."}

        initialized = self._mt5.initialize(
            path=self.settings.mt5_terminal_path,
            login=self.settings.mt5_login,
            password=self.settings.mt5_password,
            server=self.settings.mt5_server,
        )
        return {
            "connected": bool(initialized),
            "mode": "live" if self.settings.live_trading_enabled else "paper",
            "last_error": None if initialized else self._mt5.last_error(),
        }

    def account_snapshot(self) -> MT5Account:
        if self.is_live_ready:
            account = self._mt5.account_info()
            if account:
                return MT5Account(
                    balance=float(account.balance),
                    equity=float(account.equity),
                    margin=float(account.margin),
                    free_margin=float(account.margin_free),
                    currency=str(account.currency),
                )
        return MT5Account()

    def list_open_positions(self) -> list[Position]:
        if self.is_live_ready:
            raw_positions = self._mt5.positions_get() or []
            return [self._convert_position(position) for position in raw_positions]

        return [
            Position(
                symbol=order.symbol,
                side=order.side,
                volume=order.volume,
                entry_price=0,
                current_price=0,
                unrealized_loss_percent=0,
            )
            for order in self._paper_orders
        ]

    def open_order(
        self,
        *,
        symbol: str,
        side: str,
        risk_percent: float,
        stop_loss_points: float,
        take_profit_points: float,
        comment: str = "JARVIS",
    ) -> dict[str, Any]:
        account = self.account_snapshot()
        positions = self.list_open_positions()
        risk = self.risk_engine.validate_new_trade(
            symbol=symbol,
            side=side,
            balance=account.balance,
            risk_percent=risk_percent,
            stop_loss_points=stop_loss_points,
            point_value=self._point_value(symbol),
            open_positions=positions,
        )
        if risk.decision == RiskDecision.force_close:
            self.close_all(reason=risk.reason)
            return {"accepted": False, "reason": risk.reason, "mode": self._mode()}
        if risk.decision == RiskDecision.reject:
            return {"accepted": False, "reason": risk.reason, "mode": self._mode()}

        if not self.is_live_ready:
            order = PaperOrder(
                order_id=str(uuid4()),
                symbol=symbol,
                side=side,
                volume=risk.lot_size,
                stop_loss_points=stop_loss_points,
                take_profit_points=take_profit_points,
            )
            self._paper_orders.append(order)
            return {
                "accepted": True,
                "reason": "Paper order accepted.",
                "mode": "paper",
                "order_id": order.order_id,
                "volume": order.volume,
            }

        return self._send_live_order(
            symbol=symbol,
            side=side,
            volume=risk.lot_size,
            stop_loss_points=stop_loss_points,
            take_profit_points=take_profit_points,
            comment=comment,
        )

    def close_all(self, *, reason: str) -> dict[str, Any]:
        if not self.is_live_ready:
            closed = len(self._paper_orders)
            self._paper_orders.clear()
            return {"closed": closed, "mode": "paper", "reason": reason}

        # The live implementation closes each position by sending an opposite deal.
        closed = 0
        for position in self._mt5.positions_get() or []:
            tick = self._mt5.symbol_info_tick(position.symbol)
            if not tick:
                continue
            order_type = self._mt5.ORDER_TYPE_SELL if position.type == self._mt5.POSITION_TYPE_BUY else self._mt5.ORDER_TYPE_BUY
            price = tick.bid if order_type == self._mt5.ORDER_TYPE_SELL else tick.ask
            request = {
                "action": self._mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "price": price,
                "deviation": 20,
                "comment": f"JARVIS risk close: {reason}",
            }
            result = self._mt5.order_send(request)
            if result and result.retcode == self._mt5.TRADE_RETCODE_DONE:
                closed += 1
        return {"closed": closed, "mode": "live", "reason": reason}

    def terminal_state(self) -> dict[str, Any]:
        if not self._mt5:
            return {"connected": False, "charts": [], "symbols": [], "timeframes": []}

        symbols = self._mt5.symbols_get() or []
        active_symbols = [symbol.name for symbol in symbols if symbol.visible]
        # MetaTrader5 Python API cannot enumerate all open charts portably.
        return {
            "connected": bool(self._mt5.terminal_info()),
            "charts": [],
            "symbols": active_symbols[:100],
            "timeframes": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
        }

    @staticmethod
    def _load_mt5() -> Any | None:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError:
            return None
        return mt5

    def _mode(self) -> str:
        return "live" if self.is_live_ready else "paper"

    def _point_value(self, symbol: str) -> float:
        if self.is_live_ready:
            info = self._mt5.symbol_info(symbol)
            if info and info.trade_tick_value:
                return float(info.trade_tick_value)
        return 1.0

    def _send_live_order(
        self,
        *,
        symbol: str,
        side: str,
        volume: float,
        stop_loss_points: float,
        take_profit_points: float,
        comment: str,
    ) -> dict[str, Any]:
        tick = self._mt5.symbol_info_tick(symbol)
        info = self._mt5.symbol_info(symbol)
        if not tick or not info:
            return {"accepted": False, "reason": f"Symbol {symbol} is unavailable.", "mode": "live"}

        order_type = self._mt5.ORDER_TYPE_BUY if side == "buy" else self._mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "buy" else tick.bid
        point = info.point
        stop_loss = price - stop_loss_points * point if side == "buy" else price + stop_loss_points * point
        take_profit = price + take_profit_points * point if side == "buy" else price - take_profit_points * point

        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 20260515,
            "comment": comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_FOK,
        }
        result = self._mt5.order_send(request)
        accepted = bool(result and result.retcode == self._mt5.TRADE_RETCODE_DONE)
        return {
            "accepted": accepted,
            "reason": "Live order accepted." if accepted else "Live order rejected by broker.",
            "mode": "live",
            "order_id": str(result.order) if accepted else None,
            "retcode": getattr(result, "retcode", None),
        }

    def _convert_position(self, position: Any) -> Position:
        side = "buy" if position.type == self._mt5.POSITION_TYPE_BUY else "sell"
        profit = float(getattr(position, "profit", 0.0))
        volume = float(getattr(position, "volume", 0.0))
        entry_price = float(getattr(position, "price_open", 0.0))
        current_price = float(getattr(position, "price_current", 0.0))
        notional = max(abs(entry_price * volume), 1.0)
        loss_percent = abs(min(profit, 0.0)) / notional * 100
        return Position(
            symbol=position.symbol,
            side=side,
            volume=volume,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_loss_percent=loss_percent,
        )
