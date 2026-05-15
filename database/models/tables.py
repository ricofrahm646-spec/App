"""
JARVIS SQLAlchemy ORM Models.

Defines all persistent entities: trades, strategies, account snapshots,
backtest results, AI models, chat history, alerts, and settings.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.models.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Trade ────────────────────────────────────────────────────────────

class Trade(Base):
    """Individual trade record."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    close_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    close_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    strategy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", index=True
    )

    __table_args__ = (
        Index("ix_trades_symbol_status", "symbol", "status"),
        Index("ix_trades_open_time", "open_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<Trade(id={self.id}, ticket={self.ticket}, "
            f"{self.type} {self.symbol} {self.volume} lots, "
            f"status={self.status})>"
        )


# ── Strategy ─────────────────────────────────────────────────────────

class Strategy(Base):
    """Trading strategy definition and performance record."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    performance_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name!r}, status={self.status})>"


# ── Account Snapshot ─────────────────────────────────────────────────

class AccountSnapshot(Base):
    """Periodic account state capture."""

    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    free_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return (
            f"<AccountSnapshot(id={self.id}, "
            f"balance={self.balance:.2f}, equity={self.equity:.2f})>"
        )


# ── Backtest Result ──────────────────────────────────────────────────

class BacktestResult(Base):
    """Stored backtest run result."""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    equity_curve: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id})>"


# ── AI Model ─────────────────────────────────────────────────────────

class AIModel(Base):
    """AI/ML model registry entry."""

    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        Index("ix_ai_models_name_version", "name", "version"),
    )

    def __repr__(self) -> str:
        return f"<AIModel(id={self.id}, name={self.name!r}, v{self.version})>"


# ── Chat History ─────────────────────────────────────────────────────

class ChatHistory(Base):
    """Conversation log between user and JARVIS."""

    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        preview = self.content[:40] + "…" if len(self.content) > 40 else self.content
        return f"<ChatHistory(id={self.id}, role={self.role!r}, {preview!r})>"


# ── Alert ────────────────────────────────────────────────────────────

class Alert(Base):
    """Incoming alert from TradingView or other sources."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="tradingview")
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, {self.action} {self.symbol} "
            f"from {self.source})>"
        )


# ── Settings ─────────────────────────────────────────────────────────

class Settings(Base):
    """Key-value configuration store."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        display = "***" if self.encrypted else (self.value or "")[:30]
        return f"<Settings(key={self.key!r}, value={display!r})>"
