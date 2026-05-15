"""
JARVIS Trading OS - Trade Executor
Higher-level trade execution layer with pre-trade validation, retry logic,
post-trade monitoring, trailing stops, break-even management, and position sizing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import MetaTrader5 as mt5

from mt5.connector.mt5_client import MT5Client, TradeResult, AccountInfo, SymbolDetails
from mt5.utils.helpers import (
    normalize_price,
    order_type_to_string,
    pip_value,
    pips_to_price,
    price_to_pips,
    trade_comment,
    utc_now,
)

logger = logging.getLogger("jarvis.mt5.trade_executor")

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_S = 1.0
DEFAULT_MAX_SPREAD_PIPS = 5.0
DEFAULT_MIN_MARGIN_LEVEL = 150.0
MONITOR_INTERVAL_S = 1.0


@dataclass
class TradeSetup:
    """Encapsulates all parameters for a planned trade."""
    symbol: str
    order_type: int
    risk_percent: float = 1.0
    sl_pips: float = 0.0
    tp_pips: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    volume: float = 0.0
    comment: str = ""
    magic: int = 234000
    trailing_stop_pips: float = 0.0
    break_even_pips: float = 0.0
    break_even_lock_pips: float = 1.0
    max_spread_pips: float = DEFAULT_MAX_SPREAD_PIPS


@dataclass
class ManagedTrade:
    """Runtime state for a trade under active management."""
    ticket: int
    symbol: str
    order_type: int
    volume: float
    entry_price: float
    sl: float
    tp: float
    trailing_stop_pips: float = 0.0
    break_even_pips: float = 0.0
    break_even_lock_pips: float = 1.0
    break_even_applied: bool = False
    highest_profit_price: float = 0.0
    lowest_profit_price: float = float("inf")


class TradeExecutor:
    """Orchestrates trade lifecycle: validation, execution, monitoring, and management."""

    def __init__(
        self,
        client: MT5Client,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY_S,
        min_margin_level: float = DEFAULT_MIN_MARGIN_LEVEL,
        on_trade_closed: Optional[Callable[[int, float], None]] = None,
    ) -> None:
        """Initialise the executor.

        Args:
            client: Connected ``MT5Client`` instance.
            max_retries: Number of retries on transient failures.
            retry_delay: Seconds between retries.
            min_margin_level: Minimum margin level percentage required to open a trade.
            on_trade_closed: Optional callback ``(ticket, profit)`` when a managed trade closes.
        """
        self._client = client
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._min_margin_level = min_margin_level
        self._on_trade_closed = on_trade_closed
        self._managed_trades: dict[int, ManagedTrade] = {}
        self._monitor_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Pre-trade validation
    # ------------------------------------------------------------------

    def validate(self, setup: TradeSetup) -> list[str]:
        """Run all pre-trade checks against *setup*.

        Returns:
            List of validation error messages (empty means all OK).
        """
        errors: list[str] = []

        try:
            account = self._client.get_account_info()
        except Exception as exc:
            errors.append(f"Cannot retrieve account info: {exc}")
            return errors

        if account.margin_level > 0 and account.margin_level < self._min_margin_level:
            errors.append(
                f"Margin level {account.margin_level:.1f}% is below "
                f"minimum {self._min_margin_level:.1f}%"
            )

        try:
            sym = self._client.get_symbol_info(setup.symbol)
        except Exception as exc:
            errors.append(f"Cannot retrieve symbol info for {setup.symbol}: {exc}")
            return errors

        pv = pip_value(setup.symbol, sym.point, sym.digits)
        if pv > 0:
            spread_pips = (sym.spread * sym.point) / pv
            if spread_pips > setup.max_spread_pips:
                errors.append(
                    f"Spread {spread_pips:.1f} pips exceeds max {setup.max_spread_pips:.1f} pips"
                )

        positions = self._client.get_positions()
        if len(positions) >= self._client._max_open_trades:
            errors.append(
                f"Max open trades ({self._client._max_open_trades}) already reached"
            )

        for pos in positions:
            if pos["symbol"] == setup.symbol:
                if pos["type"] != setup.order_type:
                    errors.append(
                        f"Opposite position already open on {setup.symbol} "
                        f"(ticket {pos['ticket']})"
                    )
                else:
                    errors.append(
                        f"Same-direction position already open on {setup.symbol} "
                        f"(ticket {pos['ticket']})"
                    )

        if setup.sl_pips <= 0 and setup.sl_price <= 0:
            errors.append("A stop-loss (sl_pips or sl_price) is required")

        volume = setup.volume
        if volume <= 0 and setup.risk_percent > 0 and (setup.sl_pips > 0 or setup.sl_price > 0):
            pass  # volume will be calculated later
        elif volume > 0:
            if volume < sym.volume_min:
                errors.append(f"Volume {volume} below min {sym.volume_min}")
            if volume > sym.volume_max:
                errors.append(f"Volume {volume} above max {sym.volume_max}")

        return errors

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def compute_trade_parameters(self, setup: TradeSetup) -> TradeSetup:
        """Fill in computed fields (SL/TP prices, volume) on *setup*.

        Modifies and returns the same ``TradeSetup`` instance.
        """
        sym = self._client.get_symbol_info(setup.symbol)
        pv = pip_value(setup.symbol, sym.point, sym.digits)
        price = sym.ask if setup.order_type == mt5.ORDER_TYPE_BUY else sym.bid

        if setup.sl_price <= 0 and setup.sl_pips > 0:
            sl_delta = pips_to_price(setup.symbol, setup.sl_pips, sym.point, sym.digits)
            if setup.order_type == mt5.ORDER_TYPE_BUY:
                setup.sl_price = normalize_price(price - sl_delta, sym.digits)
            else:
                setup.sl_price = normalize_price(price + sl_delta, sym.digits)

        if setup.tp_price <= 0 and setup.tp_pips > 0:
            tp_delta = pips_to_price(setup.symbol, setup.tp_pips, sym.point, sym.digits)
            if setup.order_type == mt5.ORDER_TYPE_BUY:
                setup.tp_price = normalize_price(price + tp_delta, sym.digits)
            else:
                setup.tp_price = normalize_price(price - tp_delta, sym.digits)

        if setup.volume <= 0 and setup.risk_percent > 0 and setup.sl_pips > 0:
            setup.volume = self._client.calculate_lot_size(
                setup.symbol, setup.risk_percent, setup.sl_pips
            )

        if setup.volume <= 0 and setup.risk_percent > 0 and setup.sl_price > 0:
            sl_pips = price_to_pips(setup.symbol, abs(price - setup.sl_price), sym.point, sym.digits)
            if sl_pips > 0:
                setup.volume = self._client.calculate_lot_size(
                    setup.symbol, setup.risk_percent, sl_pips
                )

        return setup

    # ------------------------------------------------------------------
    # Execution with retries
    # ------------------------------------------------------------------

    def execute(self, setup: TradeSetup) -> TradeResult:
        """Validate, compute parameters, and execute a trade with retry logic.

        Args:
            setup: A fully or partially filled ``TradeSetup``.

        Returns:
            ``TradeResult`` from the final attempt.
        """
        setup = self.compute_trade_parameters(setup)

        errors = self.validate(setup)
        if errors:
            msg = "; ".join(errors)
            logger.error("Pre-trade validation failed: %s", msg)
            return TradeResult(success=False, comment=f"Validation: {msg}")

        last_result = TradeResult(success=False, comment="No attempts made")

        for attempt in range(1, self._max_retries + 1):
            logger.info(
                "Trade attempt %d/%d: %s %s %.4f lots SL=%.5f TP=%.5f",
                attempt,
                self._max_retries,
                order_type_to_string(setup.order_type),
                setup.symbol,
                setup.volume,
                setup.sl_price,
                setup.tp_price,
            )

            try:
                last_result = self._client.open_order(
                    symbol=setup.symbol,
                    order_type=setup.order_type,
                    volume=setup.volume,
                    sl=setup.sl_price,
                    tp=setup.tp_price,
                    comment=setup.comment or trade_comment(extra="executor"),
                    magic=setup.magic,
                )
            except Exception as exc:
                logger.error("Attempt %d raised exception: %s", attempt, exc)
                last_result = TradeResult(success=False, comment=str(exc))

            if last_result.success:
                logger.info("Trade executed: ticket=%d", last_result.ticket)
                self._register_managed_trade(last_result, setup)
                return last_result

            if last_result.retcode in (
                mt5.TRADE_RETCODE_REQUOTE,
                mt5.TRADE_RETCODE_PRICE_CHANGED,
                mt5.TRADE_RETCODE_TIMEOUT,
                mt5.TRADE_RETCODE_TOO_MANY_REQUESTS,
            ):
                logger.warning("Retryable error (retcode=%d), retrying…", last_result.retcode)
                time.sleep(self._retry_delay * attempt)
                continue

            logger.error(
                "Non-retryable error (retcode=%d): %s",
                last_result.retcode,
                last_result.retcode_description,
            )
            break

        return last_result

    # ------------------------------------------------------------------
    # Managed-trade registration
    # ------------------------------------------------------------------

    def _register_managed_trade(self, result: TradeResult, setup: TradeSetup) -> None:
        """Track a successfully opened trade for post-trade management."""
        managed = ManagedTrade(
            ticket=result.ticket,
            symbol=result.symbol,
            order_type=result.order_type,
            volume=result.volume,
            entry_price=result.price,
            sl=setup.sl_price,
            tp=setup.tp_price,
            trailing_stop_pips=setup.trailing_stop_pips,
            break_even_pips=setup.break_even_pips,
            break_even_lock_pips=setup.break_even_lock_pips,
            highest_profit_price=result.price,
            lowest_profit_price=result.price,
        )
        with self._lock:
            self._managed_trades[result.ticket] = managed
        self._ensure_monitor_running()

    # ------------------------------------------------------------------
    # Post-trade monitor
    # ------------------------------------------------------------------

    def _ensure_monitor_running(self) -> None:
        """Start the post-trade management thread if not already running."""
        if self._monitor_active:
            return
        self._monitor_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="jarvis-trade-monitor"
        )
        self._monitor_thread.start()
        logger.info("Trade monitor started")

    def stop_monitor(self) -> None:
        """Stop the post-trade monitoring loop."""
        self._monitor_active = False
        logger.info("Trade monitor stopped")

    def _monitor_loop(self) -> None:
        """Continuously manage open trades (trailing stop, break-even, etc.)."""
        while self._monitor_active:
            try:
                with self._lock:
                    tickets = list(self._managed_trades.keys())

                for ticket in tickets:
                    self._manage_trade(ticket)

            except Exception as exc:
                logger.error("Monitor loop error: %s", exc)
            time.sleep(MONITOR_INTERVAL_S)

    def _manage_trade(self, ticket: int) -> None:
        """Apply trailing stop and break-even logic to a single managed trade."""
        with self._lock:
            managed = self._managed_trades.get(ticket)
            if managed is None:
                return

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            with self._lock:
                closed = self._managed_trades.pop(ticket, None)
            if closed and self._on_trade_closed:
                try:
                    self._on_trade_closed(ticket, 0.0)
                except Exception:
                    pass
            return

        pos = positions[0]
        current_price = pos.price_current

        try:
            sym = self._client.get_symbol_info(managed.symbol)
        except Exception:
            return

        pv = pip_value(managed.symbol, sym.point, sym.digits)
        modified = False
        new_sl = managed.sl
        new_tp = managed.tp

        if managed.order_type == mt5.ORDER_TYPE_BUY:
            profit_distance = current_price - managed.entry_price
            managed.highest_profit_price = max(managed.highest_profit_price, current_price)
        else:
            profit_distance = managed.entry_price - current_price
            managed.lowest_profit_price = min(managed.lowest_profit_price, current_price)

        profit_pips = profit_distance / pv if pv > 0 else 0.0

        if managed.break_even_pips > 0 and not managed.break_even_applied and profit_pips >= managed.break_even_pips:
            lock_delta = pips_to_price(managed.symbol, managed.break_even_lock_pips, sym.point, sym.digits)
            if managed.order_type == mt5.ORDER_TYPE_BUY:
                be_sl = normalize_price(managed.entry_price + lock_delta, sym.digits)
                if be_sl > managed.sl:
                    new_sl = be_sl
                    modified = True
            else:
                be_sl = normalize_price(managed.entry_price - lock_delta, sym.digits)
                if be_sl < managed.sl or managed.sl == 0:
                    new_sl = be_sl
                    modified = True
            if modified:
                managed.break_even_applied = True
                logger.info(
                    "Break-even applied to ticket %d: new SL=%.5f (lock +%.1f pips)",
                    ticket,
                    new_sl,
                    managed.break_even_lock_pips,
                )

        if managed.trailing_stop_pips > 0 and profit_pips > managed.trailing_stop_pips:
            trail_delta = pips_to_price(managed.symbol, managed.trailing_stop_pips, sym.point, sym.digits)
            if managed.order_type == mt5.ORDER_TYPE_BUY:
                trail_sl = normalize_price(managed.highest_profit_price - trail_delta, sym.digits)
                if trail_sl > managed.sl:
                    new_sl = trail_sl
                    modified = True
            else:
                trail_sl = normalize_price(managed.lowest_profit_price + trail_delta, sym.digits)
                if trail_sl < managed.sl or managed.sl == 0:
                    new_sl = trail_sl
                    modified = True
            if modified:
                logger.info(
                    "Trailing stop update for ticket %d: new SL=%.5f",
                    ticket,
                    new_sl,
                )

        if modified and new_sl != managed.sl:
            result = self._client.modify_order(ticket, sl=new_sl, tp=new_tp)
            if result.success:
                with self._lock:
                    if ticket in self._managed_trades:
                        self._managed_trades[ticket].sl = new_sl
            else:
                logger.warning(
                    "Failed to modify ticket %d SL: %s", ticket, result.retcode_description
                )

    # ------------------------------------------------------------------
    # Manual management helpers
    # ------------------------------------------------------------------

    def close_trade(self, ticket: int) -> TradeResult:
        """Close a managed trade and remove it from monitoring.

        Args:
            ticket: Position ticket.

        Returns:
            ``TradeResult`` from the close operation.
        """
        result = self._client.close_order(ticket)
        with self._lock:
            self._managed_trades.pop(ticket, None)
        if result.success and self._on_trade_closed:
            try:
                self._on_trade_closed(ticket, 0.0)
            except Exception:
                pass
        return result

    def close_all(self) -> list[TradeResult]:
        """Close every managed trade."""
        with self._lock:
            tickets = list(self._managed_trades.keys())
        results: list[TradeResult] = []
        for ticket in tickets:
            results.append(self.close_trade(ticket))
        return results

    def get_managed_trades(self) -> dict[int, ManagedTrade]:
        """Return a snapshot of all trades under management."""
        with self._lock:
            return dict(self._managed_trades)

    # ------------------------------------------------------------------
    # Async wrappers
    # ------------------------------------------------------------------

    async def execute_async(self, setup: TradeSetup) -> TradeResult:
        """Run ``execute`` in a thread pool for async callers."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.execute, setup)

    async def close_trade_async(self, ticket: int) -> TradeResult:
        """Run ``close_trade`` in a thread pool for async callers."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.close_trade, ticket)
