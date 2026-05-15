"""Base strategy class for all JARVIS trading strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


@dataclass
class Signal:
    """Trading signal output from a strategy."""
    action: str           # BUY, SELL, CLOSE, HOLD
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float     # 0.0 - 1.0
    reasoning: str = ""
    timeframe: str = ""
    risk_reward: float = 0.0

    def __post_init__(self) -> None:
        if self.entry_price > 0 and self.stop_loss > 0 and self.take_profit > 0:
            sl_dist = abs(self.entry_price - self.stop_loss)
            tp_dist = abs(self.take_profit - self.entry_price)
            self.risk_reward = tp_dist / sl_dist if sl_dist > 0 else 0.0


@dataclass
class StrategyConfig:
    """Common configuration for all strategies."""
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    risk_percent: float = 2.0
    max_sl_pips: int = 50
    tp_multiplier: float = 2.0
    use_trailing_stop: bool = True
    trailing_start_pips: int = 20
    trailing_step_pips: int = 5
    magic_number: int = 12345
    max_spread_pips: int = 3
    session_filter: bool = True
    allowed_sessions: List[str] = field(default_factory=lambda: ["LONDON", "NEWYORK"])


class BaseStrategy(ABC):
    """Abstract base class for all JARVIS trading strategies."""

    name: str = "BaseStrategy"
    version: str = "1.0.0"
    strategy_type: str = "GENERIC"
    description: str = ""

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        self.config = config or StrategyConfig()
        self._indicators_cache: Dict = {}

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Analyze market data and generate a trading signal.

        Args:
            data: OHLCV DataFrame with columns [open, high, low, close, volume]
                  Index must be a DatetimeIndex, sorted ascending.

        Returns:
            Signal instance or None if no actionable signal.
        """
        ...

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators needed for the strategy."""
        ...

    def validate_signal(self, signal: Signal, spread_pips: float = 0.0) -> bool:
        """Validate signal meets minimum quality criteria."""
        if signal.confidence < 0.5:
            return False
        if signal.risk_reward < 1.5:
            return False
        if spread_pips > self.config.max_spread_pips:
            return False
        return True

    def is_session_active(self, timestamp: pd.Timestamp) -> bool:
        """Check if current time falls within allowed trading sessions."""
        if not self.config.session_filter:
            return True
        hour = timestamp.hour
        sessions = {
            "SYDNEY":   (22, 7),
            "TOKYO":    (0, 9),
            "LONDON":   (8, 17),
            "NEWYORK":  (13, 22),
        }
        for session in self.config.allowed_sessions:
            start, end = sessions.get(session, (0, 24))
            if start < end:
                if start <= hour < end:
                    return True
            else:
                if hour >= start or hour < end:
                    return True
        return False

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def _bollinger(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        mid = series.rolling(period).mean()
        std = series.rolling(period).std()
        return mid + std_dev * std, mid, mid - std_dev * std

    def __repr__(self) -> str:
        return f"{self.name} v{self.version} ({self.strategy_type}) [{self.config.symbol} {self.config.timeframe}]"
