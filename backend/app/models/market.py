import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ── Enumerations ───────────────────────────────────────────────────────────────

class MarketPhase(str, enum.Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"
    UNKNOWN = "UNKNOWN"


class AISignal(str, enum.Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


# ── Models ─────────────────────────────────────────────────────────────────────

class MarketData(Base):
    """OHLCV candle record for a given symbol and timeframe.

    Populated by the MT5 data feed or any external price provider.
    The (symbol, timeframe, timestamp) composite unique constraint
    prevents duplicate candles.
    """

    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="e.g. M1, M5, M15, H1, H4, D1"
    )

    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="Tick volume or real volume"
    )
    spread: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Broker spread in points at candle close"
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_market_data_candle"),
        Index("ix_market_data_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
        Index("ix_market_data_ts", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<MarketData id={self.id} {self.symbol} {self.timeframe} "
            f"ts={self.timestamp} close={self.close}>"
        )

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def wick_upper(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def wick_lower(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open


class AIAnalysis(Base):
    """Result of an AI/ML analysis pass on a symbol at a specific moment.

    The `indicators` JSON column stores raw indicator values (RSI, MACD, ATR…)
    alongside any model-specific outputs, allowing full post-analysis review.
    """

    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str | None] = mapped_column(String(10), nullable=True)
    model_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="e.g. lstm_v2, xgb_trend"
    )

    market_phase: Mapped[MarketPhase] = mapped_column(
        Enum(MarketPhase, name="market_phase_enum"),
        nullable=False,
        default=MarketPhase.UNKNOWN,
    )
    signal: Mapped[AISignal] = mapped_column(
        Enum(AISignal, name="ai_signal_enum"),
        nullable=False,
        default=AISignal.NEUTRAL,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Model confidence 0.0–1.0"
    )
    predicted_direction: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Regression output: positive = up, negative = down"
    )
    price_at_analysis: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Raw indicator snapshot + any model-specific fields
    indicators: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("ix_ai_analyses_symbol_created", "symbol", "created_at"),
        Index("ix_ai_analyses_signal_confidence", "signal", "confidence"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AIAnalysis id={self.id} symbol={self.symbol} "
            f"phase={self.market_phase} signal={self.signal} "
            f"confidence={self.confidence}>"
        )
