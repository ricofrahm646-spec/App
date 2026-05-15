"""
MetaTrader 5 service for the JARVIS AI Trading OS.

MT5 is Windows-only; on non-Windows environments the module is mocked so
the rest of the application can still start and serve API requests.
"""
import asyncio
import functools
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore
    MT5_AVAILABLE = False
    logger.warning(
        "MetaTrader5 package not available (non-Windows environment). "
        "MT5 features will return mock data."
    )


# ---------------------------------------------------------------------------
# Timeframe / order-type look-up tables
# ---------------------------------------------------------------------------

_TIMEFRAME_MAP: Dict[str, Any] = {
    "M1":  mt5.TIMEFRAME_M1  if MT5_AVAILABLE else 1,
    "M5":  mt5.TIMEFRAME_M5  if MT5_AVAILABLE else 5,
    "M15": mt5.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
    "M30": mt5.TIMEFRAME_M30 if MT5_AVAILABLE else 30,
    "H1":  mt5.TIMEFRAME_H1  if MT5_AVAILABLE else 16385,
    "H4":  mt5.TIMEFRAME_H4  if MT5_AVAILABLE else 16388,
    "D1":  mt5.TIMEFRAME_D1  if MT5_AVAILABLE else 16408,
    "W1":  mt5.TIMEFRAME_W1  if MT5_AVAILABLE else 32769,
    "MN1": mt5.TIMEFRAME_MN1 if MT5_AVAILABLE else 49153,
}

_ORDER_TYPE_MAP: Dict[str, Any] = {
    "BUY":       mt5.ORDER_TYPE_BUY       if MT5_AVAILABLE else 0,
    "SELL":      mt5.ORDER_TYPE_SELL      if MT5_AVAILABLE else 1,
    "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT if MT5_AVAILABLE else 2,
    "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT if MT5_AVAILABLE else 3,
    "BUY_STOP":  mt5.ORDER_TYPE_BUY_STOP  if MT5_AVAILABLE else 4,
    "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP  if MT5_AVAILABLE else 5,
}


def _run_in_executor(func, *args):
    """Execute a synchronous MT5 call on a thread-pool executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: func(*args))


class MT5Service:
    """
    Async service layer for all MetaTrader 5 interactions.

    All public methods are coroutines so they can be awaited from FastAPI
    endpoints and background tasks without blocking the event loop.
    On non-Windows systems the service automatically returns realistic mock data.
    """

    MAX_DRAWDOWN_PERCENT: float = 0.20   # 20 % → close all
    MAX_CONCURRENT_TRADES: int = 1

    def __init__(self) -> None:
        self._connected: bool = False
        self._account_login: Optional[int] = None
        self._drawdown_monitor_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self, login: int, password: str, server: str) -> bool:
        """Initialise MT5 terminal and log into the specified account."""
        if not MT5_AVAILABLE:
            logger.info("MT5 connect (mock mode) — returning success.")
            self._connected = True
            self._account_login = login
            return True
        try:
            loop = asyncio.get_event_loop()
            initialized = await loop.run_in_executor(None, mt5.initialize)
            if not initialized:
                logger.error(f"MT5 initialize() failed: {mt5.last_error()}")
                return False

            logged_in = await loop.run_in_executor(
                None, lambda: mt5.login(login, password=password, server=server)
            )
            if not logged_in:
                logger.error(f"MT5 login failed for {login}@{server}: {mt5.last_error()}")
                return False

            self._connected = True
            self._account_login = login
            logger.info(f"MT5 connected: account={login} server={server}")

            self._drawdown_monitor_task = asyncio.create_task(self.monitor_drawdown())
            return True
        except Exception as exc:
            logger.exception(f"MT5 connect error: {exc}")
            return False

    async def disconnect(self) -> None:
        """Shut down the MT5 connection and cancel background tasks."""
        if self._drawdown_monitor_task and not self._drawdown_monitor_task.done():
            self._drawdown_monitor_task.cancel()
            try:
                await self._drawdown_monitor_task
            except asyncio.CancelledError:
                pass

        if MT5_AVAILABLE:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, mt5.shutdown)

        self._connected = False
        self._account_login = None
        logger.info("MT5 disconnected.")

    async def is_connected(self) -> bool:
        """Return True if the MT5 terminal is reachable and authenticated."""
        if not self._connected:
            return False
        if not MT5_AVAILABLE:
            return True
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, mt5.account_info)
        return info is not None

    # ------------------------------------------------------------------
    # Account information
    # ------------------------------------------------------------------

    async def get_account_info(self) -> Dict:
        """Return key account metrics (balance, equity, margin, …)."""
        if not MT5_AVAILABLE:
            return self._mock_account()

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, mt5.account_info)
        if info is None:
            raise RuntimeError(f"Cannot fetch account info: {mt5.last_error()}")
        return {
            "login":        info.login,
            "name":         info.name,
            "server":       info.server,
            "currency":     info.currency,
            "leverage":     info.leverage,
            "balance":      info.balance,
            "equity":       info.equity,
            "margin":       info.margin,
            "free_margin":  info.margin_free,
            "margin_level": info.margin_level,
            "profit":       info.profit,
        }

    # ------------------------------------------------------------------
    # Trade queries
    # ------------------------------------------------------------------

    async def get_open_trades(self) -> List[Dict]:
        """Return all currently open positions."""
        if not MT5_AVAILABLE:
            return self._mock_positions()

        loop = asyncio.get_event_loop()
        positions = await loop.run_in_executor(None, mt5.positions_get)
        if positions is None:
            return []
        return [
            {
                "ticket":        p.ticket,
                "symbol":        p.symbol,
                "type":          "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume":        p.volume,
                "open_price":    p.price_open,
                "current_price": p.price_current,
                "sl":            p.sl,
                "tp":            p.tp,
                "profit":        p.profit,
                "swap":          p.swap,
                "commission":    p.commission,
                "open_time":     datetime.fromtimestamp(p.time).isoformat(),
                "comment":       p.comment,
                "magic":         p.magic,
            }
            for p in positions
        ]

    async def get_trade_history(self, days: int = 30) -> List[Dict]:
        """Return closed deal history for the last *days* calendar days."""
        if not MT5_AVAILABLE:
            return self._mock_history()

        loop = asyncio.get_event_loop()
        date_from = datetime.now() - timedelta(days=days)
        date_to = datetime.now()
        deals = await loop.run_in_executor(
            None, lambda: mt5.history_deals_get(date_from, date_to)
        )
        if deals is None:
            return []
        return [
            {
                "ticket":     d.ticket,
                "order":      d.order,
                "symbol":     d.symbol,
                "type":       d.type,
                "entry":      d.entry,
                "volume":     d.volume,
                "price":      d.price,
                "profit":     d.profit,
                "swap":       d.swap,
                "commission": d.commission,
                "time":       datetime.fromtimestamp(d.time).isoformat(),
                "comment":    d.comment,
                "magic":      d.magic,
            }
            for d in deals
        ]

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    async def place_order(
        self,
        symbol: str,
        order_type: str,
        lot: float,
        sl: float,
        tp: float,
        comment: str = "JARVIS",
        magic: int = 20240101,
    ) -> Dict:
        """
        Place a market order after validating risk constraints.

        Enforces:
        - Maximum 1 concurrent open trade.
        - No opposing direction on the same symbol.

        Returns a dict with ticket, status, price, and execution details.
        Raises ValueError for constraint violations, RuntimeError for MT5 errors.
        """
        order_type_upper = order_type.upper()
        if order_type_upper not in _ORDER_TYPE_MAP:
            raise ValueError(f"Unsupported order_type: {order_type}")

        open_trades = await self.get_open_trades()
        if len(open_trades) >= self.MAX_CONCURRENT_TRADES:
            raise ValueError(
                f"Cannot place order: {len(open_trades)} trade(s) already open. "
                "Close existing positions first."
            )

        # Check for opposing trade on same symbol
        for trade in open_trades:
            if trade["symbol"] == symbol.upper() and trade["type"] != order_type_upper:
                raise ValueError(
                    f"Opposing {trade['type']} already open for {symbol}. "
                    "Cannot place {order_type_upper}."
                )

        if not MT5_AVAILABLE:
            return self._mock_order_result(symbol, order_type_upper, lot)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: mt5.symbol_select(symbol, True))
        tick = await loop.run_in_executor(None, lambda: mt5.symbol_info_tick(symbol))
        if tick is None:
            raise RuntimeError(f"Cannot get tick for {symbol}: {mt5.last_error()}")

        is_buy = order_type_upper in ("BUY", "BUY_LIMIT", "BUY_STOP")
        price = tick.ask if is_buy else tick.bid

        sym_info = await loop.run_in_executor(None, lambda: mt5.symbol_info(symbol))
        filling = mt5.ORDER_FILLING_IOC
        if sym_info and (sym_info.filling_mode & mt5.SYMBOL_FILLING_FOK):
            filling = mt5.ORDER_FILLING_FOK

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       float(lot),
            "type":         _ORDER_TYPE_MAP[order_type_upper],
            "price":        price,
            "sl":           float(sl),
            "tp":           float(tp),
            "deviation":    20,
            "magic":        magic,
            "comment":      comment,
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        result = await loop.run_in_executor(None, lambda: mt5.order_send(request))
        if result is None:
            raise RuntimeError(f"order_send returned None: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(
                f"Order failed [retcode={result.retcode}]: {result.comment}"
            )

        logger.info(
            f"Order placed: {order_type_upper} {lot} {symbol} @ {price} "
            f"SL={sl} TP={tp} ticket={result.order}"
        )
        return {
            "ticket":  result.order,
            "symbol":  symbol,
            "type":    order_type_upper,
            "volume":  lot,
            "price":   result.price,
            "sl":      sl,
            "tp":      tp,
            "status":  "filled",
            "retcode": result.retcode,
            "comment": result.comment,
        }

    async def close_order(self, ticket: int) -> bool:
        """Close a specific open position by ticket number."""
        if not MT5_AVAILABLE:
            logger.info(f"close_order mock: ticket={ticket}")
            return True

        loop = asyncio.get_event_loop()
        positions = await loop.run_in_executor(
            None, lambda: mt5.positions_get(ticket=ticket)
        )
        if not positions:
            logger.warning(f"close_order: no open position with ticket {ticket}")
            return False

        pos = positions[0]
        is_buy_close = pos.type != mt5.ORDER_TYPE_BUY
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = await loop.run_in_executor(None, lambda: mt5.symbol_info_tick(pos.symbol))
        price = tick.bid if is_buy_close else tick.ask

        sym_info = await loop.run_in_executor(None, lambda: mt5.symbol_info(pos.symbol))
        filling = mt5.ORDER_FILLING_IOC
        if sym_info and (sym_info.filling_mode & mt5.SYMBOL_FILLING_FOK):
            filling = mt5.ORDER_FILLING_FOK

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       pos.symbol,
            "volume":       pos.volume,
            "type":         close_type,
            "position":     ticket,
            "price":        price,
            "deviation":    20,
            "magic":        pos.magic,
            "comment":      "JARVIS close",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        result = await loop.run_in_executor(None, lambda: mt5.order_send(request))
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                f"Failed to close ticket {ticket}: "
                f"{result.comment if result else mt5.last_error()}"
            )
            return False

        logger.info(f"Closed ticket={ticket} profit={pos.profit:.2f}")
        return True

    async def close_all_orders(self) -> bool:
        """Close every open position. Returns True if all closed successfully."""
        open_trades = await self.get_open_trades()
        if not open_trades:
            logger.info("close_all_orders: no open trades.")
            return True

        results = await asyncio.gather(
            *[self.close_order(t["ticket"]) for t in open_trades],
            return_exceptions=True,
        )
        all_ok = all(r is True for r in results)
        if not all_ok:
            logger.warning("close_all_orders: some positions could not be closed.")
        return all_ok

    async def modify_order(self, ticket: int, sl: float, tp: float) -> bool:
        """Modify the stop-loss and take-profit of an open position."""
        if not MT5_AVAILABLE:
            logger.info(f"modify_order mock: ticket={ticket} SL={sl} TP={tp}")
            return True

        loop = asyncio.get_event_loop()
        positions = await loop.run_in_executor(
            None, lambda: mt5.positions_get(ticket=ticket)
        )
        if not positions:
            logger.warning(f"modify_order: no position with ticket {ticket}")
            return False

        pos = positions[0]
        request = {
            "action":   mt5.TRADE_ACTION_SLTP,
            "symbol":   pos.symbol,
            "position": ticket,
            "sl":       float(sl),
            "tp":       float(tp),
        }
        result = await loop.run_in_executor(None, lambda: mt5.order_send(request))
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                f"modify_order ticket {ticket} failed: "
                f"{result.comment if result else mt5.last_error()}"
            )
            return False

        logger.info(f"Modified ticket={ticket} SL={sl} TP={tp}")
        return True

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    async def calculate_lot_size(
        self, symbol: str, risk_percent: float, sl_points: int
    ) -> float:
        """
        Calculate lot size using fixed-fractional risk management.

        Args:
            symbol:       Trading symbol.
            risk_percent: Fraction of equity to risk (e.g. 0.02 = 2 %).
            sl_points:    Stop-loss distance in MT5 points.

        Returns:
            Lot size clamped to symbol volume constraints, rounded to 2 dp.
        """
        account = await self.get_account_info()
        equity = account["equity"]

        if not MT5_AVAILABLE:
            # Simple approximation for mock mode
            risk_amount = equity * risk_percent
            risk_per_lot = sl_points * 0.10  # assume $0.10 per point per lot
            lot = max(0.01, min(100.0, round(risk_amount / risk_per_lot, 2)))
            return lot

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: mt5.symbol_select(symbol, True))
        sym_info = await loop.run_in_executor(None, lambda: mt5.symbol_info(symbol))
        if sym_info is None:
            raise RuntimeError(f"Cannot get symbol info for {symbol}")

        risk_amount   = equity * risk_percent
        tick_value    = sym_info.trade_tick_value
        tick_size     = sym_info.trade_tick_size
        point         = sym_info.point

        if tick_size == 0 or point == 0 or sl_points == 0:
            raise ValueError(f"Invalid symbol parameters: point={point} tick_size={tick_size}")

        risk_per_lot = (sl_points * point / tick_size) * tick_value
        if risk_per_lot <= 0:
            raise ValueError(f"Computed risk_per_lot is non-positive: {risk_per_lot}")

        raw_lot = risk_amount / risk_per_lot
        step    = sym_info.volume_step
        min_lot = sym_info.volume_min
        max_lot = sym_info.volume_max

        lot = round(raw_lot / step) * step
        lot = max(min_lot, min(max_lot, lot))
        return round(lot, 2)

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    async def get_symbol_info(self, symbol: str) -> Dict:
        """Return detailed symbol specifications."""
        if not MT5_AVAILABLE:
            return self._mock_symbol_info(symbol)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: mt5.symbol_select(symbol, True))
        info = await loop.run_in_executor(None, lambda: mt5.symbol_info(symbol))
        if info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")
        return {
            "symbol":               info.name,
            "description":          info.description,
            "currency_base":        info.currency_base,
            "currency_profit":      info.currency_profit,
            "currency_margin":      info.currency_margin,
            "digits":               info.digits,
            "point":                info.point,
            "spread":               info.spread,
            "trade_contract_size":  info.trade_contract_size,
            "volume_min":           info.volume_min,
            "volume_max":           info.volume_max,
            "volume_step":          info.volume_step,
            "trade_tick_size":      info.trade_tick_size,
            "trade_tick_value":     info.trade_tick_value,
            "swap_long":            info.swap_long,
            "swap_short":           info.swap_short,
            "trade_mode":           info.trade_mode,
            "filling_mode":         info.filling_mode,
        }

    async def get_current_price(self, symbol: str) -> Dict:
        """Return current bid, ask, and spread for a symbol."""
        if not MT5_AVAILABLE:
            return {"symbol": symbol, "bid": 1.08498, "ask": 1.08502,
                    "spread": 0.00004, "time": datetime.utcnow().isoformat(), "volume": 0}

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: mt5.symbol_select(symbol, True))
        tick = await loop.run_in_executor(None, lambda: mt5.symbol_info_tick(symbol))
        if tick is None:
            raise RuntimeError(f"Cannot get tick for {symbol}: {mt5.last_error()}")
        return {
            "symbol": symbol,
            "bid":    tick.bid,
            "ask":    tick.ask,
            "spread": round(tick.ask - tick.bid, 5),
            "time":   datetime.fromtimestamp(tick.time).isoformat(),
            "volume": tick.volume,
        }

    async def get_ohlcv(self, symbol: str, timeframe: str, count: int) -> List[Dict]:
        """
        Return the most recent *count* OHLCV bars.

        Args:
            symbol:    Trading symbol.
            timeframe: Timeframe string: "M1", "M5", "H1", "D1", etc.
            count:     Number of bars to fetch.

        Returns:
            List of dicts with keys: time, open, high, low, close, volume, spread.
        """
        tf = _TIMEFRAME_MAP.get(timeframe.upper())
        if tf is None:
            raise ValueError(
                f"Unknown timeframe '{timeframe}'. Valid: {list(_TIMEFRAME_MAP.keys())}"
            )

        if not MT5_AVAILABLE:
            return self._mock_ohlcv(symbol, count)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: mt5.symbol_select(symbol, True))
        rates = await loop.run_in_executor(
            None, lambda: mt5.copy_rates_from_pos(symbol, tf, 0, count)
        )
        if rates is None or len(rates) == 0:
            logger.warning(f"No OHLCV data for {symbol}/{timeframe}")
            return []
        return [
            {
                "time":   datetime.fromtimestamp(r["time"]).isoformat(),
                "open":   float(r["open"]),
                "high":   float(r["high"]),
                "low":    float(r["low"]),
                "close":  float(r["close"]),
                "volume": int(r["tick_volume"]),
                "spread": int(r["spread"]),
            }
            for r in rates
        ]

    async def get_active_charts(self) -> List[Dict]:
        """Return all charts currently open in the MT5 terminal."""
        if not MT5_AVAILABLE:
            return [
                {"chart_id": 1, "symbol": "EURUSD", "timeframe": "H1"},
                {"chart_id": 2, "symbol": "GBPUSD", "timeframe": "M15"},
            ]

        loop = asyncio.get_event_loop()
        charts: List[Dict] = []
        chart_id = await loop.run_in_executor(None, mt5.chart_first)
        while chart_id and chart_id > 0:
            symbol = await loop.run_in_executor(
                None, lambda cid=chart_id: mt5.chart_symbol_get(cid)
            )
            tf_id = await loop.run_in_executor(
                None, lambda cid=chart_id: mt5.chart_period_get(cid)
            )
            tf_name = next(
                (k for k, v in _TIMEFRAME_MAP.items() if v == tf_id), str(tf_id)
            )
            charts.append({"chart_id": chart_id, "symbol": symbol, "timeframe": tf_name})
            chart_id = await loop.run_in_executor(
                None, lambda cid=chart_id: mt5.chart_next(cid)
            )
        return charts

    # ------------------------------------------------------------------
    # Drawdown monitor
    # ------------------------------------------------------------------

    async def monitor_drawdown(self) -> None:
        """
        Background task: evaluates drawdown every 30 seconds.
        Closes all positions when drawdown >= MAX_DRAWDOWN_PERCENT.
        """
        logger.info("Drawdown monitor started.")
        while True:
            try:
                await asyncio.sleep(30)
                if not await self.is_connected():
                    continue

                account = await self.get_account_info()
                balance = account["balance"]
                equity  = account["equity"]

                if balance <= 0:
                    continue

                drawdown = (balance - equity) / balance
                if drawdown >= self.MAX_DRAWDOWN_PERCENT:
                    logger.warning(
                        f"DRAWDOWN LIMIT HIT: {drawdown*100:.1f}% >= "
                        f"{self.MAX_DRAWDOWN_PERCENT*100:.0f}%. Closing all positions."
                    )
                    await self.close_all_orders()

            except asyncio.CancelledError:
                logger.info("Drawdown monitor stopped.")
                break
            except Exception as exc:
                logger.exception(f"Drawdown monitor error: {exc}")

    # ------------------------------------------------------------------
    # Mock helpers (non-Windows / no MT5)
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_account() -> Dict:
        return {
            "login": 12345678, "name": "JARVIS Demo", "server": "MetaQuotes-Demo",
            "currency": "USD", "leverage": 100,
            "balance": 10_000.00, "equity": 10_125.50, "margin": 250.00,
            "free_margin": 9_875.50, "margin_level": 4050.20, "profit": 125.50,
        }

    @staticmethod
    def _mock_positions() -> List[Dict]:
        now = datetime.utcnow()
        return [{
            "ticket": 100001, "symbol": "EURUSD", "type": "BUY",
            "volume": 0.10, "open_price": 1.08500, "current_price": 1.08650,
            "sl": 1.08200, "tp": 1.09000, "profit": 15.00,
            "swap": -0.50, "commission": -0.70,
            "open_time": now.isoformat(), "comment": "JARVIS", "magic": 20240101,
        }]

    @staticmethod
    def _mock_history() -> List[Dict]:
        records = []
        for i in range(10):
            t = datetime.utcnow() - timedelta(days=i + 1, hours=3)
            records.append({
                "ticket": 99900 + i, "order": 99900 + i, "symbol": "EURUSD",
                "type": i % 2, "entry": 1, "volume": 0.10,
                "price": 1.08500 + i * 0.00050,
                "profit": round((5 - i) * 12.5, 2),
                "swap": -0.30, "commission": -0.70,
                "time": t.isoformat(), "comment": "JARVIS", "magic": 20240101,
            })
        return records

    @staticmethod
    def _mock_order_result(symbol: str, order_type: str, lot: float) -> Dict:
        import random
        ticket = random.randint(200_000, 299_999)
        return {
            "ticket": ticket, "symbol": symbol, "type": order_type,
            "volume": lot, "price": 1.08502, "sl": 0.0, "tp": 0.0,
            "status": "filled", "retcode": 10009,
            "comment": "Mock request executed",
        }

    @staticmethod
    def _mock_symbol_info(symbol: str) -> Dict:
        return {
            "symbol": symbol, "description": f"{symbol} Forex pair",
            "currency_base": symbol[:3], "currency_profit": symbol[3:6] if len(symbol) >= 6 else "USD",
            "currency_margin": symbol[3:6] if len(symbol) >= 6 else "USD",
            "digits": 5, "point": 1e-5, "spread": 10,
            "trade_contract_size": 100_000.0,
            "volume_min": 0.01, "volume_max": 500.0, "volume_step": 0.01,
            "trade_tick_size": 1e-5, "trade_tick_value": 1.0,
            "swap_long": -0.7, "swap_short": 0.3, "trade_mode": 4, "filling_mode": 1,
        }

    @staticmethod
    def _mock_ohlcv(symbol: str, count: int) -> List[Dict]:
        import random
        bars = []
        price = 1.08500
        now = datetime.utcnow()
        for i in range(count - 1, -1, -1):
            o = price
            h = o + random.uniform(0, 0.003)
            l = o - random.uniform(0, 0.003)  # noqa: E741
            c = random.uniform(l, h)
            bars.append({
                "time":   (now - timedelta(hours=i)).isoformat(),
                "open":   round(o, 5), "high": round(h, 5),
                "low":    round(l, 5), "close": round(c, 5),
                "volume": random.randint(500, 5000), "spread": 10,
            })
            price = c
        return bars
