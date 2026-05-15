import enum
from datetime import datetime

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from app.core.database import Base


# ── Enumerations ───────────────────────────────────────────────────────────────

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


# ── Models ─────────────────────────────────────────────────────────────────────

class Strategy(Base):
    """Trading strategy definition with live performance metrics."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    type: Mapped[StrategyType] = mapped_column(
        Enum(StrategyType, name="strategy_type_enum"), nullable=False
    )
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus, name="strategy_status_enum"),
        nullable=False,
        default=StrategyStatus.INACTIVE,
        index=True,
    )

    # Live performance counters (updated after each closed trade)
    winrate: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Win rate 0.0–100.0"
    )
    profit_factor: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Gross profit / gross loss"
    )
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loss_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Arbitrary JSON configuration (timeframes, indicators, thresholds…)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    symbols: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Comma-separated tradable symbols"
    )
    timeframes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Comma-separated timeframes, e.g. M15,H1"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    backtest_results: Mapped[list["BacktestResult"]] = relationship(
        "BacktestResult", back_populates="strategy", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_strategies_type_status", "type", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Strategy id={self.id} name={self.name} status={self.status}>"

    def update_live_stats(self, won: bool, profit: float) -> None:
        """Update rolling performance counters after a closed trade."""
        self.total_trades += 1
        if won:
            self.win_trades += 1
        else:
            self.loss_trades += 1
        self.total_profit = (self.total_profit or 0.0) + profit
        if self.total_trades > 0:
            self.winrate = (self.win_trades / self.total_trades) * 100


class BacktestResult(Base):
    """Historical backtest run result for a specific strategy and symbol."""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loss_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Percentage drawdown from peak equity"
    )
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gross_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_win: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    expectancy: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Serialised parameter set used for this run (for Optuna hyper-optimisation)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="backtest_results")

    __table_args__ = (
        Index("ix_backtest_strategy_symbol", "strategy_id", "symbol"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<BacktestResult id={self.id} strategy_id={self.strategy_id} "
            f"symbol={self.symbol} pf={self.profit_factor}>"
        )

    @property
    def winrate(self) -> float | None:
        if not self.total_trades:
            return None
        return (self.win_trades / self.total_trades) * 100
