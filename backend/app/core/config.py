from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JARVIS"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://jarvis:jarvis@postgres:5432/jarvis"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = Field(default="change-me")
    token_encryption_key: str | None = None
    mt5_data_path: Path = Path("/opt/metatrader5/MQL5")
    mt5_terminal_path: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
