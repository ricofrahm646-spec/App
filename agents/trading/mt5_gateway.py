"""MetaTrader5 gateway for live market data and optional order execution."""

from __future__ import annotations

import asyncio
import importlib
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.safety import KillSwitch


@dataclass(slots=True)
class MT5Config:
    """Configuration for MetaTrader5 terminal connectivity."""

    login: int | None = None
    password: str | None = None
    server: str | None = None
    path: str | None = None
    timeout: int = 60000
    portable: bool = False


@dataclass(slots=True)
class TradeDecision:
    """Represents normalized trade intent from strategy agents."""

    symbol: str
    side: str
    volume: float
    sl_points: int
    tp_points: int
    comment: str
    confidence: float


class MT5Gateway:
    """Async gateway wrapper around the MetaTrader5 Python API."""

    def __init__(
        self,
        config: MT5Config | None = None,
        *,
        allow_live_orders: bool = False,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        self.config = config or MT5Config()
        self.allow_live_orders = allow_live_orders
        self.kill_switch = kill_switch or KillSwitch()
        self._mt5: Any | None = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> dict[str, Any]:
        async with self._lock:
            if self._initialized:
                return {"ok": True, "status": "already_initialized"}
            self._mt5 = self._load_mt5()
            if self._mt5 is None:
                return {"ok": False, "status": "MetaTrader5 package not available"}

            payload = {
                "path": self.config.path,
                "login": self.config.login,
                "password": self.config.password,
                "server": self.config.server,
                "timeout": self.config.timeout,
                "portable": self.config.portable,
            }
            payload = {key: value for key, value in payload.items() if value is not None}

            ok = await asyncio.to_thread(self._mt5.initialize, **payload)
            if not ok:
                error = await asyncio.to_thread(self._mt5.last_error)
                return {"ok": False, "status": "initialize_failed", "error": error}
            self._initialized = True
            return {"ok": True, "status": "initialized"}

    async def shutdown(self) -> None:
        async with self._lock:
            if self._initialized and self._mt5 is not None:
                await asyncio.to_thread(self._mt5.shutdown)
            self._initialized = False

    async def account_info(self) -> dict[str, Any]:
        init = await self.initialize()
        if not init.get("ok"):
            return {
                "ok": True,
                "account": {"equity": 100.0, "balance": 100.0, "currency": "USD", "mode": "simulated"},
                "warning": init.get("status"),
            }
        account = await asyncio.to_thread(self._mt5.account_info)
        if account is None:
            error = await asyncio.to_thread(self._mt5.last_error)
            return {"ok": False, "error": error}
        return {"ok": True, "account": account._asdict()}

    async def symbol_tick(self, symbol: str) -> dict[str, Any]:
        init = await self.initialize()
        if not init.get("ok"):
            synthetic = self._synthetic_rates(symbol, count=2)
            price = synthetic[-1]["close"]
            return {"ok": True, "tick": {"bid": price - 0.0001, "ask": price + 0.0001, "mode": "simulated"}}
        await asyncio.to_thread(self._mt5.symbol_select, symbol, True)
        tick = await asyncio.to_thread(self._mt5.symbol_info_tick, symbol)
        if tick is None:
            error = await asyncio.to_thread(self._mt5.last_error)
            return {"ok": False, "error": error}
        data = tick._asdict()
        return {"ok": True, "tick": data}

    async def copy_rates(self, symbol: str, timeframe: str = "M5", count: int = 250) -> dict[str, Any]:
        init = await self.initialize()
        if not init.get("ok"):
            return {
                "ok": True,
                "rates": self._synthetic_rates(symbol, count=count),
                "mode": "simulated",
                "warning": init.get("status"),
            }
        timeframe_const = self._map_timeframe(timeframe)
        await asyncio.to_thread(self._mt5.symbol_select, symbol, True)
        rates = await asyncio.to_thread(self._mt5.copy_rates_from_pos, symbol, timeframe_const, 0, count)
        if rates is None:
            error = await asyncio.to_thread(self._mt5.last_error)
            return {"ok": False, "error": error}
        payload = []
        for row in rates:
            item = row.item() if hasattr(row, "item") else row
            if isinstance(item, tuple):
                keys = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
                payload.append(dict(zip(keys, item)))
            else:
                payload.append({key: item[key] for key in item.dtype.names})
        return {"ok": True, "rates": payload}

    async def send_order(self, decision: TradeDecision, *, magic: int = 300001) -> dict[str, Any]:
        if await self.kill_switch.is_active():
            return {"ok": False, "error": "kill_switch_active"}
        tick_resp = await self.symbol_tick(decision.symbol)
        if not tick_resp.get("ok"):
            return {"ok": False, "error": tick_resp.get("error")}
        tick = tick_resp["tick"]
        point = 0.0001 if "JPY" not in decision.symbol else 0.01
        side = decision.side.lower()
        price = tick["ask"] if side == "buy" else tick["bid"]
        sl = price - (decision.sl_points * point) if side == "buy" else price + (decision.sl_points * point)
        tp = price + (decision.tp_points * point) if side == "buy" else price - (decision.tp_points * point)

        request = {
            "action": getattr(self._mt5, "TRADE_ACTION_DEAL", 1),
            "symbol": decision.symbol,
            "volume": float(decision.volume),
            "type": getattr(self._mt5, "ORDER_TYPE_BUY" if side == "buy" else "ORDER_TYPE_SELL", 0),
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": magic,
            "comment": decision.comment[:30],
            "type_time": getattr(self._mt5, "ORDER_TIME_GTC", 0),
            "type_filling": getattr(self._mt5, "ORDER_FILLING_IOC", 1),
        }

        if not self.allow_live_orders:
            return {
                "ok": True,
                "execution_mode": "dry_run",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "request": request,
                "note": "Live execution disabled (allow_live_orders=False).",
            }

        init = await self.initialize()
        if not init.get("ok"):
            return {"ok": False, "error": init.get("status")}

        result = await asyncio.to_thread(self._mt5.order_send, request)
        if result is None:
            error = await asyncio.to_thread(self._mt5.last_error)
            return {"ok": False, "error": error, "request": request}
        payload = result._asdict() if hasattr(result, "_asdict") else {"result": str(result)}
        return {"ok": True, "execution_mode": "live", "request": request, "result": payload}

    def _load_mt5(self) -> Any | None:
        try:
            return importlib.import_module("MetaTrader5")
        except Exception:
            return None

    def _map_timeframe(self, timeframe: str) -> int:
        normalized = timeframe.strip().upper()
        if self._mt5 is None:
            return 5
        mapping = {
            "M1": self._mt5.TIMEFRAME_M1,
            "M5": self._mt5.TIMEFRAME_M5,
            "M15": self._mt5.TIMEFRAME_M15,
            "M30": self._mt5.TIMEFRAME_M30,
            "H1": self._mt5.TIMEFRAME_H1,
            "H4": self._mt5.TIMEFRAME_H4,
            "D1": self._mt5.TIMEFRAME_D1,
        }
        return mapping.get(normalized, self._mt5.TIMEFRAME_M5)

    def _synthetic_rates(self, symbol: str, *, count: int) -> list[dict[str, Any]]:
        seed = sum(ord(char) for char in symbol)
        rng = random.Random(seed)
        start = 1900.0 if symbol == "XAUUSD" else 1.08 if symbol.endswith("USD") else 100.0
        prices = [start]
        for _ in range(count):
            drift = 0.00025 if symbol == "XAUUSD" else 0.00008
            shock = rng.gauss(drift, 0.0018)
            prices.append(max(0.0001, prices[-1] * (1 + shock)))
        now = int(datetime.now(timezone.utc).timestamp())
        payload: list[dict[str, Any]] = []
        for idx in range(1, count + 1):
            open_price = prices[idx - 1]
            close_price = prices[idx]
            high = max(open_price, close_price) * (1 + abs(rng.gauss(0.0004, 0.0002)))
            low = min(open_price, close_price) * (1 - abs(rng.gauss(0.0004, 0.0002)))
            payload.append(
                {
                    "time": now - ((count - idx) * 60),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close_price,
                    "tick_volume": int(abs(rng.gauss(800, 220))),
                    "spread": 12,
                    "real_volume": 0,
                }
            )
        return payload

