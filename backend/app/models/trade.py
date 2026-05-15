import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enumerations ───────────────────────────────────────────────────────────────

class OrderType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_BUY = "CLOSE_BUY"
    CLOSE_SELL = "CLOSE_SELL"


# ── Models ─────────────────────────────────────────────────────────────────────

class Trade(Base):
    """Represents a single executed or pending trade on any connected broker."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # MT5 / broker ticket number (nullable until the order is confirmed)
    ticket: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="order_type_enum"), nullable=False
    )
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    open_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_loss: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus, name="trade_status_enum"),
        nullable=False,
        default=TradeStatus.PENDING,
        index=True,
    )

    strategy_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    magic_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_trades_symbol_status", "symbol", "status"),
        Index("ix_trades_strategy_opened", "strategy_name", "opened_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Trade id={self.id} ticket={self.ticket} symbol={self.symbol} "
            f"type={self.order_type} status={self.status}>"
        )

    @property
    def is_open(self) -> bool:
        return self.status == TradeStatus.OPEN

    @property
    def pnl_pips(self) -> float | None:
        """Rough pip calculation (not adjusted for pair decimal places)."""
        if self.open_price is None or self.close_price is None:
            return None
        diff = self.close_price - self.open_price
        return diff if self.order_type == OrderType.BUY else -diff


class TradeSignal(Base):
    """AI or strategy-generated trading signal before execution."""

    __tablename__ = "trade_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    signal_type: Mapped[SignalType] = mapped_column(
        Enum(SignalType, name="signal_type_enum"), nullable=False
    )
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Model confidence 0.0–1.0"
    )
    timeframe: Mapped[str | None] = mapped_column(String(10), nullable=True)
    executed: Mapped[bool] = mapped_column(default=False, nullable=False)
    trade_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trades.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    trade: Mapped["Trade | None"] = relationship("Trade", lazy="select")

    __table_args__ = (
        Index("ix_signals_symbol_strategy", "symbol", "strategy_name"),
        Index("ix_signals_created_executed", "created_at", "executed"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<TradeSignal id={self.id} symbol={self.symbol} "
            f"signal={self.signal_type} confidence={self.confidence}>"
        )
