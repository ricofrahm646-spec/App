from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the JARVIS backend."""

    app_name: str = "JARVIS Trading Operating System"
    environment: str = "development"
    api_prefix: str = "/api"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "postgresql+asyncpg://jarvis:jarvis@postgres:5432/jarvis"
    redis_url: str = "redis://redis:6379/0"

    encryption_key: str = "change-me-to-a-fernet-key-before-production"
    live_trading_enabled: bool = False
    paper_trading_enabled: bool = True

    mt5_terminal_path: str | None = None
    mt5_data_path: str = str(Path.home() / ".jarvis" / "mt5")
    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    max_open_trades: int = 1
    forced_close_loss_percent: float = 20.0

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    tradingview_webhook_secret: str = "change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
