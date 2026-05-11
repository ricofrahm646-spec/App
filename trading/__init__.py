"""Trading simulation package for JARVIS AI OS."""

from trading.backtester import BacktestResult, Backtester
from trading.engine import TradingEngine
from trading.risk_manager import RiskManager
from trading.strategies import (
    BreakoutStrategy,
    EmaStrategy,
    MeanReversionStrategy,
    RsiStrategy,
    StrategySignal,
)

__all__ = [
    "BacktestResult",
    "Backtester",
    "TradingEngine",
    "RiskManager",
    "StrategySignal",
    "EmaStrategy",
    "RsiStrategy",
    "BreakoutStrategy",
    "MeanReversionStrategy",
]

