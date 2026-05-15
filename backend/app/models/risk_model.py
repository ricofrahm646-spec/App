from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from app.database import Base


class RiskSettings(Base):
    __tablename__ = "risk_settings"

    id = Column(Integer, primary_key=True, index=True)
    risk_percent_per_trade = Column(Float, default=2.0)
    max_daily_loss_percent = Column(Float, default=5.0)
    max_drawdown_percent = Column(Float, default=15.0)
    max_open_trades = Column(Integer, default=5)
    max_lot_size = Column(Float, default=1.0)
    min_lot_size = Column(Float, default=0.01)
    max_spread_points = Column(Integer, default=30)
    allow_hedging = Column(Boolean, default=False)
    emergency_stop_enabled = Column(Boolean, default=False)
    emergency_stopped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # EMERGENCY_STOP, DAILY_LOSS, DRAWDOWN, etc.
    severity = Column(String(20), default="INFO")   # INFO, WARNING, CRITICAL
    message = Column(Text, nullable=False)
    data = Column(JSON, default={})
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
