"""
MT5 Service - wraps MetaTrader 5 Python API.
MT5 is Windows-only; on non-Windows environments the module is mocked so the
rest of the application can still start and serve requests.
"""
import logging
import platform
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# MT5 is only available on Windows.
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package not available (non-Windows environment). MT5 features will return mock data.")


class MT5Service:
    """Singleton-style service for MT5 operations."""

    _connected: bool = False
    _account_info: Optional[Dict] = None

    # --------------------------------------------------------------------- #
    # Connection management                                                   #
    # --------------------------------------------------------------------- #

    @classmethod
    def connect(
        cls,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            cls._connected = True
            return {"success": True, "message": "MT5 running in mock mode (non-Windows environment)"}

        kwargs: Dict[str, Any] = {}
        if path:
            kwargs["path"] = path
        if login:
            kwargs["login"] = login
        if password:
            kwargs["password"] = password
        if server:
            kwargs["server"] = server

        if not mt5.initialize(**kwargs):
            error = mt5.last_error()
            return {"success": False, "message": f"MT5 initialization failed: {error}"}

        cls._connected = True
        info = mt5.account_info()
        if info:
            cls._account_info = info._asdict()
        return {"success": True, "message": "Connected to MT5", "account": cls._account_info}

    @classmethod
    def disconnect(cls) -> Dict[str, Any]:
        if MT5_AVAILABLE and cls._connected:
            mt5.shutdown()
        cls._connected = False
        cls._account_info = None
        return {"success": True, "message": "Disconnected from MT5"}

    @classmethod
    def is_connected(cls) -> bool:
        if not MT5_AVAILABLE:
            return cls._connected
        if not cls._connected:
            return False
        try:
            info = mt5.account_info()
            return info is not None
        except Exception:
            cls._connected = False
            return False

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        connected = cls.is_connected()
        result: Dict[str, Any] = {
            "connected": connected,
            "mt5_available": MT5_AVAILABLE,
            "platform": platform.system(),
        }
        if connected and MT5_AVAILABLE:
            terminal = mt5.terminal_info()
            if terminal:
                result["terminal"] = terminal._asdict()
        return result

    # --------------------------------------------------------------------- #
    # Account                                                                 #
    # --------------------------------------------------------------------- #

    @classmethod
    def get_account_info(cls) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return cls._mock_account()
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")
        info = mt5.account_info()
        if not info:
            raise RuntimeError(f"Failed to get account info: {mt5.last_error()}")
        return info._asdict()

    # --------------------------------------------------------------------- #
    # Positions                                                               #
    # --------------------------------------------------------------------- #

    @classmethod
    def get_positions(cls, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not MT5_AVAILABLE:
            return cls._mock_positions()
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return []
        return [p._asdict() for p in positions]

    # --------------------------------------------------------------------- #
    # History                                                                 #
    # --------------------------------------------------------------------- #

    @classmethod
    def get_history(cls, days: int = 30) -> List[Dict[str, Any]]:
        if not MT5_AVAILABLE:
            return cls._mock_history()
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")
        date_from = datetime.utcnow() - timedelta(days=days)
        date_to = datetime.utcnow()
        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            return []
        return [d._asdict() for d in deals]

    # --------------------------------------------------------------------- #
    # Orders                                                                  #
    # --------------------------------------------------------------------- #

    @classmethod
    def place_order(
        cls,
        symbol: str,
        order_type: str,
        lot_size: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        comment: str = "",
        magic: int = 12345,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return cls._mock_order_result(symbol, order_type, lot_size)
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise ValueError(f"Cannot get tick for symbol: {symbol}")

        if order_type.upper() == "BUY":
            mt5_order_type = mt5.ORDER_TYPE_BUY
            exec_price = tick.ask
        else:
            mt5_order_type = mt5.ORDER_TYPE_SELL
            exec_price = tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5_order_type,
            "price": price or exec_price,
            "sl": stop_loss,
            "tp": take_profit,
            "comment": comment,
            "magic": magic,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send returned None: {mt5.last_error()}")
        res_dict = result._asdict()
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Order failed [{result.retcode}]: {result.comment}")
        return res_dict

    @classmethod
    def close_position(cls, ticket: int) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "message": "Position closed (mock)"}
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            raise ValueError(f"Position #{ticket} not found")

        pos = positions[0]
        symbol = pos.symbol
        lot = pos.volume
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise ValueError(f"Cannot get tick for {symbol}")

        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            close_price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            close_price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": close_type,
            "position": ticket,
            "price": close_price,
            "comment": "JARVIS close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"Close failed: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Close failed [{result.retcode}]: {result.comment}")
        return result._asdict()

    @classmethod
    def close_all_positions(cls) -> Dict[str, Any]:
        positions = cls.get_positions()
        closed = []
        errors = []
        for pos in positions:
            try:
                res = cls.close_position(pos["ticket"])
                closed.append(res)
            except Exception as exc:
                errors.append({"ticket": pos.get("ticket"), "error": str(exc)})
        return {"closed": len(closed), "errors": errors}

    @classmethod
    def modify_position(cls, ticket: int, stop_loss: float, take_profit: float) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return {"success": True, "ticket": ticket, "stop_loss": stop_loss, "take_profit": take_profit}
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": stop_loss,
            "tp": take_profit,
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"Modify failed: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Modify failed [{result.retcode}]: {result.comment}")
        return result._asdict()

    # --------------------------------------------------------------------- #
    # Symbol / Price                                                          #
    # --------------------------------------------------------------------- #

    @classmethod
    def get_symbol_info(cls, symbol: str) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return cls._mock_symbol_info(symbol)
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")
        info = mt5.symbol_info(symbol)
        if not info:
            raise ValueError(f"Symbol '{symbol}' not found")
        return info._asdict()

    @classmethod
    def get_price(cls, symbol: str) -> Dict[str, Any]:
        if not MT5_AVAILABLE:
            return cls._mock_price(symbol)
        if not cls.is_connected():
            raise ConnectionError("Not connected to MT5")
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise ValueError(f"Cannot get tick for '{symbol}'")
        return tick._asdict()

    @classmethod
    def get_charts(cls) -> List[Dict[str, Any]]:
        if not MT5_AVAILABLE:
            return [{"symbol": "EURUSD", "timeframe": "H1"}, {"symbol": "GBPUSD", "timeframe": "M15"}]
        # Navigator through all windows is not directly supported via API;
        # we list symbols currently subscribed.
        symbols = mt5.symbols_get()
        if not symbols:
            return []
        return [{"symbol": s.name, "visible": s.visible} for s in symbols if s.visible]

    # --------------------------------------------------------------------- #
    # Mock helpers (non-Windows)                                              #
    # --------------------------------------------------------------------- #

    @staticmethod
    def _mock_account() -> Dict[str, Any]:
        return {
            "login": 12345678,
            "trade_mode": 0,
            "leverage": 100,
            "limit_orders": 200,
            "margin_so_mode": 0,
            "trade_allowed": True,
            "trade_expert": True,
            "margin_mode": 2,
            "currency_digits": 2,
            "fifo_close": False,
            "balance": 10000.00,
            "credit": 0.00,
            "profit": 125.50,
            "equity": 10125.50,
            "margin": 250.00,
            "margin_free": 9875.50,
            "margin_level": 4050.20,
            "margin_so_call": 50.0,
            "margin_so_so": 20.0,
            "margin_initial": 0.0,
            "margin_maintenance": 0.0,
            "assets": 0.0,
            "liabilities": 0.0,
            "commission_blocked": 0.0,
            "name": "JARVIS Demo Account",
            "server": "MetaQuotes-Demo",
            "currency": "USD",
            "company": "MetaQuotes Software Corp.",
        }

    @staticmethod
    def _mock_positions() -> List[Dict[str, Any]]:
        return [
            {
                "ticket": 100001,
                "time": int(datetime.utcnow().timestamp()),
                "time_msc": int(datetime.utcnow().timestamp() * 1000),
                "time_update": int(datetime.utcnow().timestamp()),
                "time_update_msc": int(datetime.utcnow().timestamp() * 1000),
                "type": 0,
                "magic": 12345,
                "identifier": 100001,
                "reason": 0,
                "volume": 0.10,
                "price_open": 1.08500,
                "sl": 1.08200,
                "tp": 1.09000,
                "price_current": 1.08650,
                "swap": -0.50,
                "profit": 15.00,
                "symbol": "EURUSD",
                "comment": "JARVIS AI",
                "external_id": "",
            }
        ]

    @staticmethod
    def _mock_history() -> List[Dict[str, Any]]:
        records = []
        for i in range(10):
            open_time = datetime.utcnow() - timedelta(days=i + 1, hours=3)
            close_time = open_time + timedelta(hours=2)
            profit = round((5 - i) * 12.5, 2)
            records.append({
                "ticket": 99900 + i,
                "order": 99900 + i,
                "time": int(close_time.timestamp()),
                "type": i % 2,
                "entry": 1,
                "magic": 12345,
                "position_id": 99900 + i,
                "reason": 0,
                "volume": 0.10,
                "price": 1.08500 + (i * 0.00050),
                "commission": -0.70,
                "swap": -0.30,
                "profit": profit,
                "symbol": "EURUSD",
                "comment": "JARVIS AI",
            })
        return records

    @staticmethod
    def _mock_order_result(symbol: str, order_type: str, lot_size: float) -> Dict[str, Any]:
        import random
        ticket = random.randint(200000, 299999)
        return {
            "retcode": 10009,
            "deal": ticket,
            "order": ticket,
            "volume": lot_size,
            "price": 1.08500,
            "bid": 1.08498,
            "ask": 1.08502,
            "comment": "Request executed",
            "request_id": ticket,
            "retcode_external": 0,
            "symbol": symbol,
            "type": 0 if order_type.upper() == "BUY" else 1,
        }

    @staticmethod
    def _mock_symbol_info(symbol: str) -> Dict[str, Any]:
        return {
            "name": symbol,
            "custom": False,
            "chart_mode": 0,
            "select": True,
            "visible": True,
            "session_deals": 0,
            "session_buy_orders": 0,
            "session_sell_orders": 0,
            "volume": 0,
            "volumehigh": 0,
            "volumelow": 0,
            "time": int(datetime.utcnow().timestamp()),
            "digits": 5,
            "spread": 10,
            "spread_float": True,
            "ticks_bookdepth": 10,
            "trade_calc_mode": 0,
            "trade_mode": 4,
            "start_time": 0,
            "expiration_time": 0,
            "trade_stops_level": 0,
            "trade_freeze_level": 0,
            "trade_exemode": 2,
            "swap_mode": 1,
            "swap_rollover3days": 3,
            "margin_hedged_use_leg": False,
            "expiration_mode": 7,
            "filling_mode": 1,
            "order_mode": 127,
            "order_gtc_mode": 0,
            "option_mode": 0,
            "option_right": 0,
            "bid": 1.08498,
            "bidhigh": 1.09500,
            "bidlow": 1.07800,
            "ask": 1.08502,
            "askhigh": 1.09504,
            "asklow": 1.07804,
            "last": 0.0,
            "lasthigh": 0.0,
            "lastlow": 0.0,
            "volume_real": 0.0,
            "volumehigh_real": 0.0,
            "volumelow_real": 0.0,
            "option_strike": 0.0,
            "point": 1e-05,
            "trade_tick_value": 1.0,
            "trade_tick_value_profit": 1.0,
            "trade_tick_value_loss": 1.0,
            "trade_tick_size": 1e-05,
            "trade_contract_size": 100000.0,
            "trade_accrued_interest": 0.0,
            "trade_face_value": 0.0,
            "trade_liquidity_rate": 0.0,
            "volume_min": 0.01,
            "volume_max": 500.0,
            "volume_step": 0.01,
            "volume_limit": 0.0,
            "swap_long": -0.7,
            "swap_short": 0.3,
            "margin_initial": 0.0,
            "margin_maintenance": 0.0,
            "session_volume": 0.0,
            "session_turnover": 0.0,
            "session_interest": 0.0,
            "session_buy_orders_volume": 0.0,
            "session_sell_orders_volume": 0.0,
            "session_open": 0.0,
            "session_close": 0.0,
            "session_aw": 0.0,
            "session_price_settlement": 0.0,
            "session_price_limit_min": 0.0,
            "session_price_limit_max": 0.0,
            "margin_hedged": 0.0,
            "price_change": 0.0,
            "price_volatility": 0.0,
            "price_theoretical": 0.0,
            "price_greeks_delta": 0.0,
            "price_greeks_theta": 0.0,
            "price_greeks_gamma": 0.0,
            "price_greeks_vega": 0.0,
            "price_greeks_rho": 0.0,
            "price_greeks_omega": 0.0,
            "price_sensitivity": 0.0,
            "basis": "",
            "category": "",
            "currency_base": symbol[:3] if len(symbol) >= 3 else symbol,
            "currency_profit": symbol[3:6] if len(symbol) >= 6 else "USD",
            "currency_margin": symbol[3:6] if len(symbol) >= 6 else "USD",
            "bank": "",
            "description": f"{symbol} Forex pair",
            "exchange": "",
            "formula": "",
            "isin": "",
            "page": "",
            "path": f"Forex\\{symbol}",
        }

    @staticmethod
    def _mock_price(symbol: str) -> Dict[str, Any]:
        return {
            "time": int(datetime.utcnow().timestamp()),
            "bid": 1.08498,
            "ask": 1.08502,
            "last": 0.0,
            "volume": 0,
            "time_msc": int(datetime.utcnow().timestamp() * 1000),
            "flags": 6,
            "volume_real": 0.0,
        }
