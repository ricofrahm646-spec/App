"""Mock MT5 connector backed by an in-memory price simulator.

It produces realistic geometric-brownian-motion price feeds, holds open
positions, evaluates P/L continuously and respects SL/TP. Used for local dev,
CI, backtesting and any environment where the real terminal isn't present.
"""
from __future__ import annotations

import asyncio
import itertools
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.app.core.logging_setup import logger
from backend.app.schemas.common import AccountSnapshot, TradeRequest, TradeView


_DEFAULT_SYMBOLS = (
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "US30", "NAS100", "SPX500",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Position:
    ticket: int
    symbol: str
    side: str
    volume: float
    entry_price: float
    sl: float | None = None
    tp: float | None = None
    opened_at: datetime = field(default_factory=_now)


class MockMT5Connector:
    def __init__(self, starting_balance: float = 10_000.0) -> None:
        self._connected = True
        self._balance = starting_balance
        self._equity = starting_balance
        self._currency = "USD"
        self._leverage = 100
        self._ticket_counter = itertools.count(start=1_000_001)
        self._positions: dict[int, _Position] = {}
        self._closed: list[TradeView] = []
        self._prices: dict[str, float] = self._seed_prices()
        self._last_tick = time.time()
        self._lock = asyncio.Lock()

    # ─────────────────────────────── price simulator ──────────────
    @staticmethod
    def _seed_prices() -> dict[str, float]:
        return {
            "EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 156.30, "USDCHF": 0.9050,
            "USDCAD": 1.3650, "AUDUSD": 0.6650, "NZDUSD": 0.6150,
            "XAUUSD": 2350.0, "XAGUSD": 28.50,
            "BTCUSD": 65_000.0, "ETHUSD": 3_400.0,
            "US30": 39_800.0, "NAS100": 17_900.0, "SPX500": 5_300.0,
        }

    def _advance_prices(self) -> None:
        now = time.time()
        dt = max(now - self._last_tick, 1e-3)
        self._last_tick = now
        for symbol, price in self._prices.items():
            vol = 0.0006 if "USD" in symbol[:6] and "BTC" not in symbol else 0.003
            shock = random.gauss(0.0, vol) * math.sqrt(dt / 60.0)
            self._prices[symbol] = max(price * (1.0 + shock), 0.0001)

    # ─────────────────────────────── lifecycle ────────────────────
    async def is_connected(self) -> bool:
        return self._connected

    async def symbols(self) -> list[str]:
        return list(_DEFAULT_SYMBOLS)

    async def price(self, symbol: str) -> float:
        self._advance_prices()
        return self._prices.get(symbol.upper(), 1.0)

    # ─────────────────────────────── trading ──────────────────────
    async def open(self, req: TradeRequest) -> TradeView:
        async with self._lock:
            self._advance_prices()
            symbol = req.symbol.upper()
            price = self._prices.get(symbol)
            if price is None:
                price = 1.0
                self._prices[symbol] = price
            ticket = next(self._ticket_counter)
            pos = _Position(
                ticket=ticket,
                symbol=symbol,
                side=req.side,
                volume=req.volume,
                entry_price=price,
                sl=req.sl,
                tp=req.tp,
            )
            self._positions[ticket] = pos
            logger.info("[MOCK] Opened {} {} {} @ {}", req.side, req.volume, symbol, price)
            return self._to_view(pos)

    async def close(self, ticket: int) -> TradeView | None:
        async with self._lock:
            pos = self._positions.pop(ticket, None)
            if not pos:
                return None
            exit_price = self._prices.get(pos.symbol, pos.entry_price)
            profit = self._pnl(pos, exit_price)
            self._balance += profit
            view = TradeView(
                ticket=pos.ticket,
                symbol=pos.symbol,
                side=pos.side,  # type: ignore[arg-type]
                volume=pos.volume,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                sl=pos.sl,
                tp=pos.tp,
                profit=profit,
                status="closed",
                opened_at=pos.opened_at,
                closed_at=_now(),
            )
            self._closed.append(view)
            logger.info("[MOCK] Closed #{} pnl={:.2f}", pos.ticket, profit)
            return view

    async def close_all(self) -> int:
        tickets = list(self._positions.keys())
        for t in tickets:
            await self.close(t)
        return len(tickets)

    async def modify(self, ticket: int, sl: float | None = None, tp: float | None = None) -> bool:
        async with self._lock:
            pos = self._positions.get(ticket)
            if not pos:
                return False
            if sl is not None:
                pos.sl = sl
            if tp is not None:
                pos.tp = tp
            return True

    async def open_positions(self) -> list[TradeView]:
        self._advance_prices()
        return [self._to_view(p) for p in self._positions.values()]

    async def history(self, limit: int = 50) -> list[TradeView]:
        return list(self._closed[-limit:][::-1])

    async def account_snapshot(self) -> AccountSnapshot:
        self._advance_prices()
        floating = sum(
            self._pnl(p, self._prices.get(p.symbol, p.entry_price))
            for p in self._positions.values()
        )
        margin = sum(p.volume * 1000 for p in self._positions.values())
        equity = self._balance + floating
        return AccountSnapshot(
            balance=round(self._balance, 2),
            equity=round(equity, 2),
            margin=round(margin, 2),
            free_margin=round(max(equity - margin, 0.0), 2),
            profit=round(floating, 2),
            currency=self._currency,
            leverage=self._leverage,
            server="MOCK",
        )

    # ─────────────────────────────── helpers ──────────────────────
    def _pnl(self, pos: _Position, price: float) -> float:
        sign = 1.0 if pos.side == "BUY" else -1.0
        pip_value = 100_000.0 if "JPY" not in pos.symbol else 1_000.0
        return sign * (price - pos.entry_price) * pos.volume * pip_value / 1000.0

    def _to_view(self, pos: _Position) -> TradeView:
        price = self._prices.get(pos.symbol, pos.entry_price)
        return TradeView(
            ticket=pos.ticket,
            symbol=pos.symbol,
            side=pos.side,  # type: ignore[arg-type]
            volume=pos.volume,
            entry_price=pos.entry_price,
            exit_price=None,
            sl=pos.sl,
            tp=pos.tp,
            profit=round(self._pnl(pos, price), 2),
            status="open",
            opened_at=pos.opened_at,
            closed_at=None,
        )
