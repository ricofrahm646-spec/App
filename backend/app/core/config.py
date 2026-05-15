from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "JARVIS Trading OS"
    app_version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Security ─────────────────────────────────────────────────────────
    secret_key: str = Field(default="change-me-in-production-jarvis-secret-key-2024")
    encryption_key: str = Field(default="")
    api_key_header: str = "X-API-Key"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    algorithm: str = "HS256"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./jarvis.db"
    db_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5

    # ── MetaTrader 5 ─────────────────────────────────────────────────────
    mt5_host: str = "localhost"
    mt5_port: int = 8001
    mt5_account: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    mt5_path: str = ""
    mt5_timeout: int = 30000
    mt5_reconnect_interval: int = 5

    # ── Telegram ─────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_notifications_enabled: bool = False
    telegram_trade_alerts: bool = True
    telegram_error_alerts: bool = True
    telegram_daily_summary: bool = True

    # ── TradingView ──────────────────────────────────────────────────────
    tradingview_webhook_secret: str = ""
    tradingview_allowed_ips: list[str] = []
    tradingview_auto_execute: bool = False

    # ── AI / LLM ─────────────────────────────────────────────────────────
    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.7
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    ai_chat_history_limit: int = 100
    ai_system_prompt: str = (
        "You are JARVIS, an advanced AI trading assistant. "
        "You help traders analyze markets, develop strategies, "
        "and manage their trading operations."
    )

    # ── Backtesting ──────────────────────────────────────────────────────
    backtest_default_capital: float = 10000.0
    backtest_default_commission: float = 0.0002
    backtest_max_concurrent: int = 4
    backtest_data_dir: str = "./data/historical"

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: LogLevel = LogLevel.INFO
    log_dir: str = "./logs"
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_backup_count: int = 5
    log_json_format: bool = True

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("tradingview_allowed_ips", mode="before")
    @classmethod
    def parse_ips(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    return Settings()
