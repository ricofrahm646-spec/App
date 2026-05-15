from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration for the JARVIS Trading OS backend.

    All values can be overridden via environment variables or a ``.env`` file
    located at the project root.
    """

    APP_NAME: str = "JARVIS Trading OS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jarvis:jarvis@localhost:5432/jarvis"
    DATABASE_SYNC_URL: str = "postgresql://jarvis:jarvis@localhost:5432/jarvis"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ENCRYPTION_KEY: str = "change-me-32-byte-key-for-fernet"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # MT5
    MT5_PATH: str = ""
    MT5_LOGIN: int = 0
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""
    MT5_DATA_PATH: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # TradingView
    TRADINGVIEW_WEBHOOK_SECRET: str = ""

    # AI
    AI_MODEL_PATH: str = "./ai/models/saved"
    OPENAI_API_KEY: str = ""

    # Risk Management
    MAX_RISK_PER_TRADE: float = 0.02
    MAX_DAILY_LOSS: float = 0.05
    MAX_DRAWDOWN: float = 0.20
    MAX_CONCURRENT_TRADES: int = 1
    EMERGENCY_STOP_LOSS_PCT: float = 0.20

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
