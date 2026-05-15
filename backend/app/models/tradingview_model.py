from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from app.database import Base


class TradingViewConfig(Base):
    __tablename__ = "tradingview_configs"

    id = Column(Integer, primary_key=True, index=True)
    webhook_secret = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradingViewSignal(Base):
    __tablename__ = "tradingview_signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)  # BUY / SELL / CLOSE / CLOSE_LONG / CLOSE_SHORT
    order_type = Column(String(20), nullable=True)
    price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    comment = Column(String(200), nullable=True)
    raw_payload = Column(JSON, default={})
    processed = Column(Boolean, default=False)
    trade_ticket = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
