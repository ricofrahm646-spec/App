"""Live MetaTrader 5 connector — thin wrapper around the official `MetaTrader5` lib.

This module only imports the MetaTrader5 package when instantiated, so the rest
of the platform runs on Linux/macOS where the package is not installable.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.core.config import settings
from backend.app.core.logging_setup import logger
from backend.app.schemas.common import AccountSnapshot, TradeRequest, TradeView


class LiveMT5Connector:
    def __init__(self) -> None:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]

        self._mt5 = mt5
        kwargs: dict[str, object] = {}
        if settings.mt5_path:
            kwargs["path"] = settings.mt5_path
        if not mt5.initialize(**kwargs):
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        if settings.mt5_login:
            ok = mt5.login(
                int(settings.mt5_login),
                password=settings.mt5_password,
                server=settings.mt5_server,
            )
            if not ok:
                raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")
        logger.info("Connected to MT5 server={}", settings.mt5_server or "default")

    # ─────────────────────────────── helpers ──────────────────────
    async def _to_thread(self, fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def is_connected(self) -> bool:
        info = await self._to_thread(self._mt5.terminal_info)
        return bool(info)

    async def account_snapshot(self) -> AccountSnapshot:
        info = await self._to_thread(self._mt5.account_info)
        if info is None:
            raise RuntimeError("MT5 account_info unavailable")
        return AccountSnapshot(
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            profit=info.profit,
            currency=info.currency,
            leverage=info.leverage,
            server=info.server,
        )

    async def symbols(self) -> list[str]:
        symbols = await self._to_thread(self._mt5.symbols_get)
        return [s.name for s in symbols] if symbols else []

    async def price(self, symbol: str) -> float:
        tick = await self._to_thread(self._mt5.symbol_info_tick, symbol)
        if not tick:
            raise RuntimeError(f"No tick for {symbol}")
        return float(tick.ask)

    async def open(self, req: TradeRequest) -> TradeView:
        mt5 = self._mt5
        side = mt5.ORDER_TYPE_BUY if req.side == "BUY" else mt5.ORDER_TYPE_SELL
        tick = await self._to_thread(mt5.symbol_info_tick, req.symbol)
        price = tick.ask if req.side == "BUY" else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": req.symbol,
            "volume": req.volume,
            "type": side,
            "price": price,
            "sl": req.sl or 0.0,
            "tp": req.tp or 0.0,
            "deviation": 10,
            "magic": 88_001,
            "comment": req.comment or "jarvis",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = await self._to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 order_send failed: {result and result.comment}")
        return TradeView(
            ticket=result.order,
            symbol=req.symbol,
            side=req.side,
            volume=req.volume,
            entry_price=price,
            sl=req.sl,
            tp=req.tp,
            profit=0.0,
            status="open",
            opened_at=datetime.now(timezone.utc),
        )

    async def close(self, ticket: int) -> TradeView | None:
        mt5 = self._mt5
        positions = await self._to_thread(mt5.positions_get, ticket=ticket)
        if not positions:
            return None
        pos = positions[0]
        side = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = await self._to_thread(mt5.symbol_info_tick, pos.symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": side,
            "position": pos.ticket,
            "price": price,
            "deviation": 10,
            "magic": 88_001,
            "comment": "jarvis-close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = await self._to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 close failed: {result and result.comment}")
        return TradeView(
            ticket=pos.ticket,
            symbol=pos.symbol,
            side="BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
            volume=pos.volume,
            entry_price=pos.price_open,
            exit_price=price,
            sl=pos.sl,
            tp=pos.tp,
            profit=pos.profit,
            status="closed",
            opened_at=datetime.fromtimestamp(pos.time, tz=timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )

    async def close_all(self) -> int:
        positions = await self._to_thread(self._mt5.positions_get)
        n = 0
        for p in positions or []:
            if await self.close(p.ticket):
                n += 1
        return n

    async def modify(self, ticket: int, sl: float | None = None, tp: float | None = None) -> bool:
        mt5 = self._mt5
        positions = await self._to_thread(mt5.positions_get, ticket=ticket)
        if not positions:
            return False
        pos = positions[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": pos.ticket,
            "sl": sl if sl is not None else pos.sl,
            "tp": tp if tp is not None else pos.tp,
        }
        result = await self._to_thread(mt5.order_send, request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE

    async def open_positions(self) -> list[TradeView]:
        positions = await self._to_thread(self._mt5.positions_get)
        if not positions:
            return []
        return [
            TradeView(
                ticket=p.ticket,
                symbol=p.symbol,
                side="BUY" if p.type == self._mt5.ORDER_TYPE_BUY else "SELL",
                volume=p.volume,
                entry_price=p.price_open,
                exit_price=None,
                sl=p.sl,
                tp=p.tp,
                profit=p.profit,
                status="open",
                opened_at=datetime.fromtimestamp(p.time, tz=timezone.utc),
            )
            for p in positions
        ]

    async def history(self, limit: int = 50) -> list[TradeView]:
        # Pulls last N deals — left as a thin shim; the mock provides richer data.
        return []
