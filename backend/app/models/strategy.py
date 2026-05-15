"""
Strategy model for the JARVIS Trading OS (sync SQLite system).
"""
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
)

from app.database import Base


class StrategyType(str, enum.Enum):
    SCALPING = "SCALPING"
    ICT = "ICT"
    TREND = "TREND"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT = "BREAKOUT"
    GRID = "GRID"
    ARBITRAGE = "ARBITRAGE"
    ML_BASED = "ML_BASED"
    HYBRID = "HYBRID"
    CUSTOM = "CUSTOM"


class StrategyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TESTING = "TESTING"
    PAUSED = "PAUSED"
    DEPRECATED = "DEPRECATED"


class Strategy(Base):
    """Trading strategy definition with live performance metrics."""

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)

    type = Column(Enum(StrategyType), nullable=False, default=StrategyType.CUSTOM)
    status = Column(Enum(StrategyStatus), nullable=False, default=StrategyStatus.INACTIVE, index=True)

    # Live performance counters
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    total_loss = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    avg_trade_duration = Column(Float, default=0.0)

    # Configuration
    config = Column(JSON, default={})
    symbols = Column(Text, nullable=True)
    timeframes = Column(Text, nullable=True)
    source_code = Column(Text, nullable=True)

    # AI generation metadata
    is_ai_generated = Column(Boolean, default=False)
    ai_model_used = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    last_trade_at = Column(DateTime, nullable=True)
