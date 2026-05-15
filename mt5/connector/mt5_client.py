"""MetaTrader 5 connection and trading client."""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class TradeRequest:
    symbol: str
    order_type: OrderType
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""
    magic: int = 234000


@dataclass
class TradeResult:
    success: bool
    order_id: Optional[int] = None
    price: float = 0.0
    volume: float = 0.0
    error: str = ""


@dataclass
class AccountInfo:
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    profit: float = 0.0
    leverage: int = 0
    currency: str = "USD"


@dataclass
class SymbolInfo:
    name: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: int = 0
    digits: int = 0
    point: float = 0.0
    trade_tick_value: float = 0.0
    trade_contract_size: float = 0.0
    volume_min: float = 0.0
    volume_max: float = 0.0
    volume_step: float = 0.0


class MT5Client:
    """Client for interacting with MetaTrader 5."""

    def __init__(self, path: str = "", login: int = 0, password: str = "", server: str = ""):
        self._path = path
        self._login = login
        self._password = password
        self._server = server
        self._connected = False
        self._mt5 = None

    async def connect(self) -> bool:
        """Initialize and connect to MT5 terminal."""
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5

            init_params: Dict[str, Any] = {}
            if self._path:
                init_params["path"] = self._path
            if self._login:
                init_params["login"] = self._login
                init_params["password"] = self._password
                init_params["server"] = self._server

            result = await asyncio.to_thread(mt5.initialize, **init_params)
            if not result:
                error = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error}")
                return False

            self._connected = True
            logger.info("MT5 connected successfully")
            return True
        except ImportError:
            logger.warning("MetaTrader5 package not available - running in simulation mode")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False

    async def disconnect(self) -> None:
        if self._mt5 and self._connected:
            await asyncio.to_thread(self._mt5.shutdown)
            self._connected = False
            logger.info("MT5 disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get_account_info(self) -> AccountInfo:
        if not self._connected or not self._mt5:
            return AccountInfo()
        info = await asyncio.to_thread(self._mt5.account_info)
        if info is None:
            return AccountInfo()
        return AccountInfo(
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            profit=info.profit,
            leverage=info.leverage,
            currency=info.currency,
        )

    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        if not self._connected or not self._mt5:
            return None
        info = await asyncio.to_thread(self._mt5.symbol_info, symbol)
        if info is None:
            return None
        return SymbolInfo(
            name=info.name, bid=info.bid, ask=info.ask,
            spread=info.spread, digits=info.digits, point=info.point,
            trade_tick_value=info.trade_tick_value,
            trade_contract_size=info.trade_contract_size,
            volume_min=info.volume_min, volume_max=info.volume_max,
            volume_step=info.volume_step,
        )

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        if not self._connected or not self._mt5:
            return []
        positions = await asyncio.to_thread(self._mt5.positions_get)
        if positions is None:
            return []
        return [p._asdict() for p in positions]

    async def open_trade(self, request: TradeRequest) -> TradeResult:
        """Open a new trade. Enforces max 1 concurrent trade and no simultaneous buy+sell."""
        if not self._connected or not self._mt5:
            return TradeResult(success=False, error="MT5 not connected")

        positions = await self.get_open_positions()
        if len(positions) >= 1:
            return TradeResult(success=False, error="Maximum concurrent trades reached (1)")

        for pos in positions:
            if pos.get("symbol") == request.symbol:
                existing_type = "buy" if pos.get("type") == 0 else "sell"
                if existing_type != request.order_type.value:
                    return TradeResult(
                        success=False,
                        error=f"Cannot open {request.order_type.value} - {existing_type} already open on {request.symbol}"
                    )

        symbol_info = await self.get_symbol_info(request.symbol)
        if not symbol_info:
            return TradeResult(success=False, error=f"Symbol {request.symbol} not found")

        mt5 = self._mt5
        price = symbol_info.ask if request.order_type == OrderType.BUY else symbol_info.bid
        order_type = mt5.ORDER_TYPE_BUY if request.order_type == OrderType.BUY else mt5.ORDER_TYPE_SELL

        trade_request: Dict[str, Any] = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": request.magic,
            "comment": request.comment or "JARVIS",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if request.sl:
            trade_request["sl"] = request.sl
        if request.tp:
            trade_request["tp"] = request.tp

        result = await asyncio.to_thread(mt5.order_send, trade_request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = result.comment if result else "Unknown error"
            return TradeResult(success=False, error=error_msg)

        return TradeResult(
            success=True, order_id=result.order, price=result.price, volume=result.volume,
        )

    async def close_trade(self, ticket: int) -> TradeResult:
        """Close a trade by ticket number."""
        if not self._connected or not self._mt5:
            return TradeResult(success=False, error="MT5 not connected")

        mt5 = self._mt5
        position = None
        positions = await asyncio.to_thread(mt5.positions_get, ticket=ticket)
        if positions:
            position = positions[0]
        if not position:
            return TradeResult(success=False, error=f"Position {ticket} not found")

        close_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        symbol_info = await self.get_symbol_info(position.symbol)
        if not symbol_info:
            return TradeResult(success=False, error=f"Symbol info not available for {position.symbol}")
        price = symbol_info.bid if position.type == 0 else symbol_info.ask

        request: Dict[str, Any] = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": position.magic,
            "comment": "JARVIS close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = await asyncio.to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(success=False, error=result.comment if result else "Unknown")
        return TradeResult(success=True, order_id=result.order, price=result.price, volume=result.volume)

    async def modify_trade(self, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> TradeResult:
        """Modify SL/TP of an existing position."""
        if not self._connected or not self._mt5:
            return TradeResult(success=False, error="MT5 not connected")
        mt5 = self._mt5
        positions = await asyncio.to_thread(mt5.positions_get, ticket=ticket)
        if not positions:
            return TradeResult(success=False, error=f"Position {ticket} not found")
        pos = positions[0]
        request: Dict[str, Any] = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl if sl is not None else pos.sl,
            "tp": tp if tp is not None else pos.tp,
        }
        result = await asyncio.to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(success=False, error=result.comment if result else "Unknown")
        return TradeResult(success=True, order_id=result.order)

    async def get_historical_data(self, symbol: str, timeframe: str, count: int = 1000) -> List[Dict[str, Any]]:
        """Get historical OHLCV data."""
        if not self._connected or not self._mt5:
            return []
        mt5 = self._mt5
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1,
        }
        tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        rates = await asyncio.to_thread(mt5.copy_rates_from_pos, symbol, tf, 0, count)
        if rates is None:
            return []
        import pandas as pd
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df.to_dict("records")

    async def calculate_lot_size(self, symbol: str, risk_pct: float, sl_pips: float, account_balance: Optional[float] = None) -> float:
        """Calculate optimal lot size based on risk percentage and SL distance."""
        info = await self.get_account_info()
        balance = account_balance or info.balance
        if balance <= 0 or sl_pips <= 0:
            return 0.01

        sym = await self.get_symbol_info(symbol)
        if not sym:
            return 0.01

        risk_amount = balance * risk_pct
        pip_value = sym.trade_tick_value * (sl_pips / sym.point) if sym.point > 0 else 1
        if pip_value <= 0:
            return 0.01

        lot_size = risk_amount / (sl_pips * pip_value)
        lot_size = max(sym.volume_min, min(lot_size, sym.volume_max))
        lot_size = round(lot_size / sym.volume_step) * sym.volume_step if sym.volume_step > 0 else lot_size
        return round(lot_size, 2)
