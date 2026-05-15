"""
JARVIS Trading OS - MT5 Connector Package
==========================================

Provides a production-grade interface to MetaTrader 5 with built-in safety
rules, account monitoring, and market data services.

Quick start::

    from mt5 import MT5Client, TradeExecutor, AccountMonitor, MarketDataProvider

    client = MT5Client(login=12345, password="secret", server="Broker-Server")
    client.connect()

    executor = TradeExecutor(client)
    monitor  = AccountMonitor(client)
    market   = MarketDataProvider(client)
"""

from mt5.connector.mt5_client import (
    MT5Client,
    TradeResult,
    AccountInfo,
    SymbolDetails,
)
from mt5.connector.trade_executor import (
    TradeExecutor,
    TradeSetup,
    ManagedTrade,
)
from mt5.connector.account_monitor import (
    AccountMonitor,
    AccountSnapshot,
    DrawdownState,
)
from mt5.connector.market_data import (
    MarketDataProvider,
    PriceTick,
    VolatilityInfo,
    SpreadStats,
    TradingSession,
)

__all__ = [
    "MT5Client",
    "TradeResult",
    "AccountInfo",
    "SymbolDetails",
    "TradeExecutor",
    "TradeSetup",
    "ManagedTrade",
    "AccountMonitor",
    "AccountSnapshot",
    "DrawdownState",
    "MarketDataProvider",
    "PriceTick",
    "VolatilityInfo",
    "SpreadStats",
    "TradingSession",
]
