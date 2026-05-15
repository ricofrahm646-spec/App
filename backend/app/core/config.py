from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JARVIS API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "postgresql://jarvis:jarvis@postgres:5432/jarvis"
    redis_url: str = "redis://redis:6379/0"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    mt5_terminal_path: str = ""
    mt5_data_path: str = ""
    emergency_stop_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
