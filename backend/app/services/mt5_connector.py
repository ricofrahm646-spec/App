"""MetaTrader 5 connector with graceful degradation when MT5 is unavailable."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    mt5 = None


@dataclass
class AccountSnapshot:
    balance: float | None
    equity: float | None
    margin: float | None
    margin_free: float | None
    server: str | None
    currency: str | None


class MT5Connector:
    """Thin wrapper around the official MetaTrader5 Python package."""

    def __init__(self) -> None:
        self._initialized = False

    def ensure_initialized(self) -> bool:
        if mt5 is None:
            logger.warning("MetaTrader5 package not available in this environment")
            return False
        if self._initialized:
            return True
        kwargs: dict[str, Any] = {}
        if settings.mt5_path:
            kwargs["path"] = settings.mt5_path
        ok = bool(mt5.initialize(**kwargs))
        if ok and settings.mt5_login and settings.mt5_password and settings.mt5_server:
            authorized = mt5.login(
                int(settings.mt5_login),
                password=settings.mt5_password,
                server=settings.mt5_server,
            )
            if not authorized:
                logger.error("MT5 login failed: %s", mt5.last_error())
                mt5.shutdown()
                return False
        self._initialized = ok
        if not ok:
            logger.error("MT5 initialize failed: %s", mt5.last_error() if mt5 else "n/a")
        return ok

    def shutdown(self) -> None:
        if mt5 and self._initialized:
            mt5.shutdown()
        self._initialized = False

    def account_info(self) -> AccountSnapshot | None:
        if not self.ensure_initialized() or mt5 is None:
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return AccountSnapshot(
            balance=float(info.balance),
            equity=float(info.equity),
            margin=float(info.margin),
            margin_free=float(info.margin_free),
            server=str(info.server),
            currency=str(info.currency),
        )

    def positions(self) -> list[dict[str, Any]]:
        if not self.ensure_initialized() or mt5 is None:
            return []
        positions = mt5.positions_get()
        if positions is None:
            return []
        out: list[dict[str, Any]] = []
        for p in positions:
            out.append(
                {
                    "ticket": int(p.ticket),
                    "symbol": p.symbol,
                    "type": "buy" if p.type == mt5.POSITION_TYPE_BUY else "sell",
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "sl": float(p.sl),
                    "tp": float(p.tp),
                    "profit": float(p.profit),
                }
            )
        return out

    def symbol_info(self, symbol: str) -> dict[str, Any] | None:
        if not self.ensure_initialized() or mt5 is None:
            return None
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return {
            "symbol": info.name,
            "bid": float(info.bid),
            "ask": float(info.ask),
            "point": float(info.point),
            "digits": int(info.digits),
        }

    def order_send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Delegates to mt5.order_send; caller must satisfy broker constraints."""
        if not self.ensure_initialized() or mt5 is None:
            return {"retcode": "ERROR", "comment": "MT5 not available"}
        result = mt5.order_send(request)
        if result is None:
            return {"retcode": "NONE", "comment": str(mt5.last_error())}
        return {
            "retcode": int(result.retcode),
            "order": int(result.order) if result.order else None,
            "deal": int(result.deal) if result.deal else None,
            "comment": result.comment,
        }
