import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "JARVIS AI Trading OS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "jarvis-secret-key-change-in-production")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jarvis_trading.db")

    # MT5
    MT5_PATH: Optional[str] = os.getenv("MT5_PATH", None)
    MT5_LOGIN: Optional[int] = int(os.getenv("MT5_LOGIN", "0")) or None
    MT5_PASSWORD: Optional[str] = os.getenv("MT5_PASSWORD", None)
    MT5_SERVER: Optional[str] = os.getenv("MT5_SERVER", None)

    # AI / LLM
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)
    DEFAULT_AI_MODEL: str = os.getenv("DEFAULT_AI_MODEL", "gpt-4o")
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "4096"))
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.7"))

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", None)
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID", None)

    # TradingView
    TRADINGVIEW_WEBHOOK_SECRET: Optional[str] = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", None)

    # MQL5 / MT5 file paths
    MT5_EXPERTS_PATH: str = os.getenv("MT5_EXPERTS_PATH", "/MT5/MQL5/Experts")
    MT5_INDICATORS_PATH: str = os.getenv("MT5_INDICATORS_PATH", "/MT5/MQL5/Indicators")
    GENERATED_FILES_DIR: str = os.getenv("GENERATED_FILES_DIR", "./generated")

    # Risk defaults
    DEFAULT_RISK_PERCENT: float = float(os.getenv("DEFAULT_RISK_PERCENT", "2.0"))
    DEFAULT_MAX_DAILY_LOSS: float = float(os.getenv("DEFAULT_MAX_DAILY_LOSS", "5.0"))
    DEFAULT_MAX_DRAWDOWN: float = float(os.getenv("DEFAULT_MAX_DRAWDOWN", "15.0"))
    DEFAULT_MAX_OPEN_TRADES: int = int(os.getenv("DEFAULT_MAX_OPEN_TRADES", "5"))

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
