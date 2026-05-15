from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    jarvis_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_db: str = "jarvis"
    postgres_user: str = "jarvis"
    postgres_password: str = "jarvis"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_host: str = "redis"
    redis_port: int = 6379

    mt5_terminal_path: str = "/opt/mt5/terminal64.exe"
    mt5_data_path: str = "/opt/mt5/data"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    tradingview_webhook_secret: str = ""

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
