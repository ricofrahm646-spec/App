from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "JARVIS Trading OS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://jarvis:jarvis@localhost:5432/jarvis_db",
        description="Async PostgreSQL connection string (asyncpg driver)",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
    )

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        description="JWT signing secret – set a stable value in .env",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Fernet symmetric key for encrypting sensitive fields (base64url, 32 bytes)
    FERNET_KEY: Optional[str] = Field(
        default=None,
        description="Base64-encoded Fernet key for field-level encryption. "
                    "Generate with: from cryptography.fernet import Fernet; Fernet.generate_key()",
    )

    # ── MetaTrader 5 ───────────────────────────────────────────────────────────
    MT5_LOGIN: Optional[int] = None
    MT5_PASSWORD: Optional[str] = None
    MT5_SERVER: Optional[str] = None
    MT5_PATH: str = "C:/Program Files/MetaTrader 5"

    # ── Telegram ───────────────────────────────────────────────────────────────
    TELEGRAM_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None

    # ── TradingView ────────────────────────────────────────────────────────────
    TRADINGVIEW_WEBHOOK_SECRET: Optional[str] = None

    # ── Risk Management ────────────────────────────────────────────────────────
    MAX_TRADES: int = Field(default=1, ge=1, le=100)
    MAX_DRAWDOWN_PERCENT: float = Field(default=20.0, gt=0.0, le=100.0)
    DEFAULT_LOT_SIZE: float = 0.01
    MAX_LOT_SIZE: float = 1.0

    # ── CORS ───────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # ── Celery ─────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return upper

    @field_validator("MAX_DRAWDOWN_PERCENT")
    @classmethod
    def validate_drawdown(cls, v: float) -> float:
        if v <= 0 or v > 100:
            raise ValueError("MAX_DRAWDOWN_PERCENT must be between 0 and 100")
        return v


settings = Settings()
