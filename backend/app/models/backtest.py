import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Enum, Text, ForeignKey
from app.database import Base


class BacktestStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    strategy_name = Column(String(200), nullable=False)
    status = Column(Enum(BacktestStatus), default=BacktestStatus.PENDING)

    # Parameters
    symbol = Column(String(50), nullable=False)
    timeframe = Column(String(20), nullable=False)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    initial_capital = Column(Float, default=10000.0)
    commission = Column(Float, default=0.0001)
    slippage = Column(Float, default=0.0001)
    backtest_type = Column(String(50), default="standard")  # standard, walkforward, montecarlo

    # Results
    final_balance = Column(Float, nullable=True)
    total_return = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    winning_trades = Column(Integer, nullable=True)
    losing_trades = Column(Integer, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    avg_trade_duration = Column(Float, nullable=True)
    max_consecutive_wins = Column(Integer, nullable=True)
    max_consecutive_losses = Column(Integer, nullable=True)

    # Serialized trade list and equity curve
    trades_data = Column(JSON, default=[])
    equity_curve = Column(JSON, default=[])
    monthly_returns = Column(JSON, default={})
    detailed_results = Column(JSON, default={})

    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
