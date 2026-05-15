"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    fernet_key: str | None = Field(
        default=None,
        description="32-byte url-safe base64 Fernet key; generated at runtime if unset",
    )

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://jarvis:jarvis@localhost:5432/jarvis",
    )
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    cors_origins: str = "http://localhost:3000"

    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_path: str | None = Field(
        default=None,
        description="Path to terminal64.exe folder (Windows) or MetaTrader 5 root",
    )

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    tradingview_webhook_secret: str | None = None

    jarvis_workspace_root: str = Field(
        default="..",
        description="Repo root for generated artifacts (relative to backend cwd or absolute)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
