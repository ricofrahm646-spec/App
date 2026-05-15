"""
JARVIS Trading OS - MT5 Client
Low-level wrapper around the MetaTrader5 Python package with built-in
safety rules, auto-reconnect, and loss control.

Safety rules enforced:
  1. Never open BUY and SELL simultaneously on the same symbol.
  2. Maximum 1 trade open at a time (globally).
  3. Auto-close any trade that reaches 20 % loss.
  4. Every order has mandatory SL (loss control on every trade).
"""

from __future__ import annotations

import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import MetaTrader5 as mt5

from mt5.utils.helpers import (
    calculate_lot_size,
    normalize_price,
    opposite_order_type,
    order_type_to_string,
    pip_value,
    pips_to_price,
    resolve_timeframe,
    trade_comment,
    utc_now,
)

logger = logging.getLogger("jarvis.mt5.client")

MAX_OPEN_TRADES = 1
MAX_LOSS_PERCENT = 20.0
AUTO_RECONNECT_DELAY_S = 2.0
MAX_RECONNECT_ATTEMPTS = 5


@dataclass
class TradeResult:
    """Wrapper around the result of a trade operation."""
    success: bool
    ticket: int = 0
    order_type: int = -1
    symbol: str = ""
    volume: float = 0.0
    price: float = 0.0
    comment: str = ""
    retcode: int = 0
    retcode_description: str = ""
    raw: Any = None


@dataclass
class AccountInfo:
    """Snapshot of the trading account."""
    login: int = 0
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    profit: float = 0.0
    currency: str = ""
    leverage: int = 0
    server: str = ""
    name: str = ""


@dataclass
class SymbolDetails:
    """Key attributes of a trading symbol."""
    name: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: int = 0
    digits: int = 0
    point: float = 0.0
    trade_contract_size: float = 0.0
    volume_min: float = 0.0
    volume_max: float = 0.0
    volume_step: float = 0.0
    trade_tick_value: float = 0.0
    trade_tick_size: float = 0.0
    swap_long: float = 0.0
    swap_short: float = 0.0
    raw: Any = None


class MT5Client:
    """Thread-safe MetaTrader 5 client with safety rules and auto-reconnect."""

    def __init__(
        self,
        path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        timeout: int = 10_000,
        max_loss_percent: float = MAX_LOSS_PERCENT,
        max_open_trades: int = MAX_OPEN_TRADES,
    ) -> None:
        """Initialise the MT5 client.

        Args:
            path: Path to the MetaTrader 5 terminal executable.
            login: Account number.
            password: Account password.
            server: Broker server name.
            timeout: Connection timeout in milliseconds.
            max_loss_percent: Auto-close threshold (percentage of entry price).
            max_open_trades: Maximum simultaneous open trades.
        """
        self._path = path
        self._login = login
        self._password = password
        self._server = server
        self._timeout = timeout
        self._max_loss_percent = max_loss_percent
        self._max_open_trades = max_open_trades
        self._connected = False
        self._lock = threading.Lock()
        self._loss_monitor_active = False
        self._loss_monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Initialise and log in to the MT5 terminal.

        Retries up to ``MAX_RECONNECT_ATTEMPTS`` on failure.

        Returns:
            True on successful connection.
        """
        with self._lock:
            for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
                init_kwargs: dict[str, Any] = {}
                if self._path:
                    init_kwargs["path"] = self._path
                if self._login is not None:
                    init_kwargs["login"] = self._login
                if self._password:
                    init_kwargs["password"] = self._password
                if self._server:
                    init_kwargs["server"] = self._server
                if self._timeout:
                    init_kwargs["timeout"] = self._timeout

                if mt5.initialize(**init_kwargs):
                    self._connected = True
                    logger.info("MT5 connected (attempt %d)", attempt)
                    self._start_loss_monitor()
                    return True

                err = mt5.last_error()
                logger.warning(
                    "MT5 connection attempt %d/%d failed: %s",
                    attempt,
                    MAX_RECONNECT_ATTEMPTS,
                    err,
                )
                time.sleep(AUTO_RECONNECT_DELAY_S)

            self._connected = False
            logger.error("MT5 connection failed after %d attempts", MAX_RECONNECT_ATTEMPTS)
            return False

    def disconnect(self) -> None:
        """Shutdown the MT5 connection and stop background monitors."""
        with self._lock:
            self._loss_monitor_active = False
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 disconnected")

    def is_connected(self) -> bool:
        """Return True if the terminal is initialised and responsive."""
        info = mt5.terminal_info()
        if info is None:
            self._connected = False
            return False
        self._connected = info.connected
        return self._connected

    def _ensure_connected(self) -> None:
        """Reconnect automatically if the terminal went away."""
        if not self.is_connected():
            logger.warning("MT5 connection lost — attempting reconnect")
            if not self.connect():
                raise ConnectionError("Unable to re-establish MT5 connection")

    # ------------------------------------------------------------------
    # Account information
    # ------------------------------------------------------------------

    def get_account_info(self) -> AccountInfo:
        """Retrieve current account metrics.

        Returns:
            An ``AccountInfo`` dataclass.

        Raises:
            ConnectionError: If not connected.
            RuntimeError: If MT5 returns no data.
        """
        self._ensure_connected()
        info = mt5.account_info()
        if info is None:
            raise RuntimeError(f"account_info() failed: {mt5.last_error()}")
        return AccountInfo(
            login=info.login,
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level if info.margin_level else 0.0,
            profit=info.profit,
            currency=info.currency,
            leverage=info.leverage,
            server=info.server,
            name=info.name,
        )

    # ------------------------------------------------------------------
    # Symbol information
    # ------------------------------------------------------------------

    def get_symbol_info(self, symbol: str) -> SymbolDetails:
        """Get details for a trading symbol.

        Args:
            symbol: Instrument name (e.g. ``EURUSD``).

        Returns:
            A ``SymbolDetails`` dataclass.

        Raises:
            RuntimeError: If the symbol is not found.
        """
        self._ensure_connected()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Symbol '{symbol}' could not be selected: {mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"symbol_info('{symbol}') returned None: {mt5.last_error()}")
        return SymbolDetails(
            name=info.name,
            bid=info.bid,
            ask=info.ask,
            spread=info.spread,
            digits=info.digits,
            point=info.point,
            trade_contract_size=info.trade_contract_size,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            trade_tick_value=info.trade_tick_value,
            trade_tick_size=info.trade_tick_size,
            swap_long=info.swap_long,
            swap_short=info.swap_short,
            raw=info,
        )

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Return all open positions, optionally filtered by symbol.

        Args:
            symbol: If given, only positions on this symbol are returned.

        Returns:
            List of position dicts.
        """
        self._ensure_connected()
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        result: list[dict[str, Any]] = []
        for pos in positions:
            result.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": pos.type,
                "type_str": order_type_to_string(pos.type),
                "volume": pos.volume,
                "price_open": pos.price_open,
                "price_current": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "swap": pos.swap,
                "time": datetime.fromtimestamp(pos.time, tz=timezone.utc),
                "comment": pos.comment,
                "magic": pos.magic,
            })
        return result

    # ------------------------------------------------------------------
    # Pre-trade safety checks
    # ------------------------------------------------------------------

    def _validate_new_order(self, symbol: str, order_type: int) -> None:
        """Enforce safety rules before opening a new order.

        Raises:
            RuntimeError: If a rule is violated.
        """
        positions = self.get_positions()

        if len(positions) >= self._max_open_trades:
            raise RuntimeError(
                f"Maximum open trades ({self._max_open_trades}) reached. "
                "Close existing positions first."
            )

        for pos in positions:
            if pos["symbol"] == symbol:
                existing_type = pos["type"]
                if (
                    (order_type == mt5.ORDER_TYPE_BUY and existing_type == mt5.ORDER_TYPE_SELL)
                    or (order_type == mt5.ORDER_TYPE_SELL and existing_type == mt5.ORDER_TYPE_BUY)
                ):
                    raise RuntimeError(
                        f"Cannot open {order_type_to_string(order_type)} on {symbol} — "
                        f"an opposite {order_type_to_string(existing_type)} position "
                        f"(ticket {pos['ticket']}) is already open. "
                        "Simultaneous BUY and SELL on the same symbol is forbidden."
                    )
                raise RuntimeError(
                    f"A {order_type_to_string(existing_type)} position on {symbol} "
                    f"(ticket {pos['ticket']}) is already open."
                )

    # ------------------------------------------------------------------
    # Order operations
    # ------------------------------------------------------------------

    def open_order(
        self,
        symbol: str,
        order_type: int,
        volume: float,
        sl: float,
        tp: float,
        comment: str = "",
        magic: int = 234000,
        deviation: int = 20,
    ) -> TradeResult:
        """Open a market order with full safety checks.

        Args:
            symbol: Instrument name.
            order_type: ``mt5.ORDER_TYPE_BUY`` or ``mt5.ORDER_TYPE_SELL``.
            volume: Lot size.
            sl: Stop-loss price (**required** — loss control rule).
            tp: Take-profit price.
            comment: Order comment.
            magic: EA magic number.
            deviation: Maximum allowed slippage in points.

        Returns:
            A ``TradeResult``.

        Raises:
            ValueError: If SL is not provided (loss control).
            RuntimeError: If safety rules are violated.
        """
        self._ensure_connected()

        if sl <= 0:
            raise ValueError("Stop-loss (sl) is mandatory for every trade — loss control rule.")

        self._validate_new_order(symbol, order_type)

        sym = self.get_symbol_info(symbol)
        price = sym.ask if order_type == mt5.ORDER_TYPE_BUY else sym.bid

        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": normalize_price(sl, sym.digits),
            "tp": normalize_price(tp, sym.digits) if tp > 0 else 0.0,
            "deviation": deviation,
            "magic": magic,
            "comment": comment or trade_comment(),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        logger.info(
            "Opening %s %s %.2f lots | SL=%.5f TP=%.5f",
            order_type_to_string(order_type),
            symbol,
            volume,
            sl,
            tp,
        )

        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            logger.error("order_send returned None: %s", err)
            return TradeResult(success=False, retcode=-1, retcode_description=str(err))

        success = result.retcode == mt5.TRADE_RETCODE_DONE
        trade_result = TradeResult(
            success=success,
            ticket=result.order if success else 0,
            order_type=order_type,
            symbol=symbol,
            volume=volume,
            price=result.price if success else 0.0,
            comment=request["comment"],
            retcode=result.retcode,
            retcode_description=self._retcode_description(result.retcode),
            raw=result,
        )

        if success:
            logger.info("Order opened: ticket=%d price=%.5f", trade_result.ticket, trade_result.price)
        else:
            logger.error(
                "Order failed: retcode=%d (%s)", result.retcode, trade_result.retcode_description
            )

        return trade_result

    def close_order(self, ticket: int, deviation: int = 20) -> TradeResult:
        """Close an open position by ticket number.

        Args:
            ticket: Position ticket.
            deviation: Maximum slippage in points.

        Returns:
            A ``TradeResult``.

        Raises:
            RuntimeError: If the position is not found.
        """
        self._ensure_connected()

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            raise RuntimeError(f"Position with ticket {ticket} not found")

        pos = positions[0]
        sym = self.get_symbol_info(pos.symbol)

        close_type = opposite_order_type(pos.type)
        price = sym.ask if close_type == mt5.ORDER_TYPE_BUY else sym.bid

        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": pos.magic,
            "comment": f"close|{ticket}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        logger.info("Closing ticket %d (%s %.2f lots)", ticket, pos.symbol, pos.volume)

        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            logger.error("close_order send returned None: %s", err)
            return TradeResult(success=False, retcode=-1, retcode_description=str(err))

        success = result.retcode == mt5.TRADE_RETCODE_DONE
        trade_result = TradeResult(
            success=success,
            ticket=ticket,
            order_type=close_type,
            symbol=pos.symbol,
            volume=pos.volume,
            price=result.price if success else 0.0,
            retcode=result.retcode,
            retcode_description=self._retcode_description(result.retcode),
            raw=result,
        )

        if success:
            logger.info("Position %d closed at %.5f", ticket, trade_result.price)
        else:
            logger.error("Failed to close %d: %d (%s)", ticket, result.retcode, trade_result.retcode_description)

        return trade_result

    def close_all_orders(self) -> list[TradeResult]:
        """Emergency close of every open position.

        Returns:
            List of ``TradeResult`` for each close attempt.
        """
        self._ensure_connected()
        positions = self.get_positions()
        results: list[TradeResult] = []
        for pos in positions:
            try:
                res = self.close_order(pos["ticket"])
                results.append(res)
            except Exception as exc:
                logger.error("Error closing ticket %d: %s", pos["ticket"], exc)
                results.append(TradeResult(success=False, ticket=pos["ticket"], comment=str(exc)))
        logger.info("close_all_orders: %d positions processed", len(results))
        return results

    def modify_order(self, ticket: int, sl: float, tp: float) -> TradeResult:
        """Modify the SL and TP of an existing position.

        Args:
            ticket: Position ticket.
            sl: New stop-loss price.
            tp: New take-profit price.

        Returns:
            A ``TradeResult``.

        Raises:
            RuntimeError: If the position is not found.
        """
        self._ensure_connected()

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            raise RuntimeError(f"Position with ticket {ticket} not found")

        pos = positions[0]
        sym = self.get_symbol_info(pos.symbol)

        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": normalize_price(sl, sym.digits),
            "tp": normalize_price(tp, sym.digits) if tp > 0 else 0.0,
        }

        logger.info("Modifying ticket %d: SL=%.5f TP=%.5f", ticket, sl, tp)

        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            logger.error("modify_order send returned None: %s", err)
            return TradeResult(success=False, retcode=-1, retcode_description=str(err))

        success = result.retcode == mt5.TRADE_RETCODE_DONE
        trade_result = TradeResult(
            success=success,
            ticket=ticket,
            symbol=pos.symbol,
            retcode=result.retcode,
            retcode_description=self._retcode_description(result.retcode),
            raw=result,
        )

        if success:
            logger.info("Position %d modified successfully", ticket)
        else:
            logger.error("Failed to modify %d: %d (%s)", ticket, result.retcode, trade_result.retcode_description)

        return trade_result

    # ------------------------------------------------------------------
    # Lot-size calculator
    # ------------------------------------------------------------------

    def calculate_lot_size(
        self,
        symbol: str,
        risk_percent: float,
        sl_pips: float,
    ) -> float:
        """Calculate lot size from risk percentage and SL distance.

        Args:
            symbol: Instrument name.
            risk_percent: Risk as a percentage of balance (e.g. 1.0 = 1 %).
            sl_pips: Stop-loss distance in pips.

        Returns:
            Lot size.
        """
        self._ensure_connected()
        account = self.get_account_info()
        sym = self.get_symbol_info(symbol)
        pv = pip_value(symbol, sym.point, sym.digits)
        pip_value_per_lot = (pv / sym.point) * sym.trade_tick_value if sym.point else sym.trade_tick_value

        return calculate_lot_size(
            balance=account.balance,
            risk_percent=risk_percent,
            sl_pips=sl_pips,
            pip_value_per_lot=pip_value_per_lot,
            min_lot=sym.volume_min,
            max_lot=sym.volume_max,
            lot_step=sym.volume_step,
        )

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    def get_history_orders(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve historical deals within a date range.

        Args:
            from_date: Start of the range (defaults to 30 days ago).
            to_date: End of the range (defaults to now).

        Returns:
            List of deal dicts.
        """
        self._ensure_connected()
        if from_date is None:
            from_date = utc_now() - timedelta(days=30)
        if to_date is None:
            to_date = utc_now()

        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            logger.warning("history_deals_get returned None: %s", mt5.last_error())
            return []

        result: list[dict[str, Any]] = []
        for deal in deals:
            result.append({
                "ticket": deal.ticket,
                "order": deal.order,
                "symbol": deal.symbol,
                "type": deal.type,
                "volume": deal.volume,
                "price": deal.price,
                "profit": deal.profit,
                "swap": deal.swap,
                "commission": deal.commission,
                "time": datetime.fromtimestamp(deal.time, tz=timezone.utc),
                "comment": deal.comment,
                "magic": deal.magic,
                "entry": deal.entry,
            })
        return result

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def get_tick_data(self, symbol: str, count: int = 1000) -> list[dict[str, Any]]:
        """Fetch the most recent ticks for a symbol.

        Args:
            symbol: Instrument name.
            count: Number of ticks to retrieve.

        Returns:
            List of tick dicts with bid, ask, time, etc.
        """
        self._ensure_connected()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select symbol '{symbol}': {mt5.last_error()}")

        ticks = mt5.copy_ticks_from(symbol, utc_now(), count, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            logger.warning("No tick data for %s: %s", symbol, mt5.last_error())
            return []

        result: list[dict[str, Any]] = []
        for t in ticks:
            result.append({
                "time": datetime.fromtimestamp(t["time"], tz=timezone.utc),
                "bid": float(t["bid"]),
                "ask": float(t["ask"]),
                "last": float(t["last"]),
                "volume": float(t["volume"]),
                "flags": int(t["flags"]),
            })
        return result

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str | int = "H1",
        count: int = 500,
    ) -> list[dict[str, Any]]:
        """Get OHLCV (candlestick) data.

        Args:
            symbol: Instrument name.
            timeframe: Timeframe string (e.g. ``"H1"``) or MT5 constant.
            count: Number of bars to retrieve.

        Returns:
            List of bar dicts with open/high/low/close/volume/time.
        """
        self._ensure_connected()
        tf = resolve_timeframe(timeframe)
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select symbol '{symbol}': {mt5.last_error()}")

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning("No OHLCV data for %s %s: %s", symbol, timeframe, mt5.last_error())
            return []

        result: list[dict[str, Any]] = []
        for bar in rates:
            result.append({
                "time": datetime.fromtimestamp(bar["time"], tz=timezone.utc),
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
                "tick_volume": int(bar["tick_volume"]),
                "spread": int(bar["spread"]),
                "real_volume": int(bar["real_volume"]),
            })
        return result

    # ------------------------------------------------------------------
    # Open charts detection
    # ------------------------------------------------------------------

    def get_open_charts(self) -> list[dict[str, Any]]:
        """Detect charts currently open in the terminal.

        MT5 Python API does not expose chart windows directly; this method
        uses the terminal's symbol list filtered by ``visible`` flag and
        returns symbols that are currently selected/visible in Market Watch,
        which approximates the set of open charts.

        Returns:
            List of dicts with symbol name and basic info.
        """
        self._ensure_connected()
        symbols = mt5.symbols_get()
        if symbols is None:
            return []

        charts: list[dict[str, Any]] = []
        for sym in symbols:
            if sym.visible:
                charts.append({
                    "symbol": sym.name,
                    "bid": sym.bid,
                    "ask": sym.ask,
                    "spread": sym.spread,
                    "digits": sym.digits,
                    "trade_mode": sym.trade_mode,
                    "description": sym.description,
                })
        return charts

    # ------------------------------------------------------------------
    # Background loss monitor
    # ------------------------------------------------------------------

    def _start_loss_monitor(self) -> None:
        """Spawn a daemon thread that watches open positions for the 20 % loss rule."""
        if self._loss_monitor_active:
            return
        self._loss_monitor_active = True
        self._loss_monitor_thread = threading.Thread(
            target=self._loss_monitor_loop, daemon=True, name="jarvis-loss-monitor"
        )
        self._loss_monitor_thread.start()
        logger.info("Loss monitor started (threshold=%.1f%%)", self._max_loss_percent)

    def _loss_monitor_loop(self) -> None:
        """Continuously check positions against the max-loss rule."""
        while self._loss_monitor_active:
            try:
                if not self.is_connected():
                    time.sleep(5)
                    continue

                positions = mt5.positions_get()
                if positions:
                    for pos in positions:
                        self._check_loss_threshold(pos)
            except Exception as exc:
                logger.error("Loss monitor error: %s", exc)
            time.sleep(1)

    def _check_loss_threshold(self, pos) -> None:
        """Auto-close a position if its floating loss exceeds the threshold.

        The threshold is defined as a percentage of the position's notional
        value at entry (price_open * volume * contract_size).
        """
        if pos.profit >= 0:
            return

        try:
            sym_info = mt5.symbol_info(pos.symbol)
            if sym_info is None:
                return
            notional = pos.price_open * pos.volume * sym_info.trade_contract_size
            if notional == 0:
                return
            loss_percent = (abs(pos.profit) / notional) * 100.0

            if loss_percent >= self._max_loss_percent:
                logger.warning(
                    "LOSS CONTROL: ticket %d (%s) loss %.2f%% >= %.2f%% — auto-closing",
                    pos.ticket,
                    pos.symbol,
                    loss_percent,
                    self._max_loss_percent,
                )
                self.close_order(pos.ticket)
        except Exception as exc:
            logger.error("Loss threshold check failed for ticket %d: %s", pos.ticket, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _retcode_description(retcode: int) -> str:
        """Map an MT5 retcode to a human-readable message."""
        descriptions: dict[int, str] = {
            mt5.TRADE_RETCODE_REQUOTE: "Requote",
            mt5.TRADE_RETCODE_REJECT: "Request rejected",
            mt5.TRADE_RETCODE_CANCEL: "Request cancelled by trader",
            mt5.TRADE_RETCODE_PLACED: "Order placed",
            mt5.TRADE_RETCODE_DONE: "Request completed",
            mt5.TRADE_RETCODE_DONE_PARTIAL: "Only part of the request completed",
            mt5.TRADE_RETCODE_ERROR: "Request processing error",
            mt5.TRADE_RETCODE_TIMEOUT: "Request cancelled by timeout",
            mt5.TRADE_RETCODE_INVALID: "Invalid request",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
            mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade disabled",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "Market closed",
            mt5.TRADE_RETCODE_NO_MONEY: "Insufficient funds",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "Price changed",
            mt5.TRADE_RETCODE_PRICE_OFF: "No quotes to process",
            mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid expiration date",
            mt5.TRADE_RETCODE_ORDER_CHANGED: "Order state changed",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too many requests",
        }
        return descriptions.get(retcode, f"Unknown retcode ({retcode})")
