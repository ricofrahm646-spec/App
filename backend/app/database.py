from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all JARVIS SQLite tables."""
    from app.models.strategy import Strategy  # noqa: F401
    from app.models.backtest import BacktestResult  # noqa: F401
    from app.models.telegram_model import TelegramConfig, TelegramMessage  # noqa: F401
    from app.models.tradingview_model import TradingViewConfig, TradingViewSignal  # noqa: F401
    from app.models.risk_model import RiskSettings, RiskEvent  # noqa: F401
    Base.metadata.create_all(bind=engine)
