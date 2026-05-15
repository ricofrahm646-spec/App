from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "JARVIS API"
    app_env: str = "development"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    postgres_db: str = "jarvis"
    postgres_user: str = "jarvis"
    postgres_password: str = "jarvis_secure_password"
    postgres_port: int = 5432
    redis_port: int = 6379

    jarvis_allowed_workspace: Path = Field(default=ROOT_DIR)
    jarvis_max_single_trade_risk: float = 0.01
    jarvis_max_account_drawdown: float = 0.20
    jarvis_max_floating_loss_close: float = 0.20

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    tradingview_shared_secret: str | None = None

    mt5_login: str | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_path: str | None = None

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@postgres:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://redis:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
