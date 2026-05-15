"""Centralised application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Strongly typed settings object — single source of truth for the platform."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "JARVIS"
    app_port: int = 8000
    frontend_port: int = 3000
    secret_key: str = "change-me"
    encryption_key: str = ""

    # ── Database ──────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://jarvis:jarvis@localhost:5432/jarvis"
    redis_url: str = "redis://localhost:6379/0"

    # ── MT5 ───────────────────────────────────────────────────────
    mt5_login: str = ""
    mt5_password: str = ""
    mt5_server: str = ""
    mt5_path: str = ""
    mt5_mock: bool = True
    mt5_data_path: str = ""

    # ── LLM ───────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "local"] = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # ── Telegram ──────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ── TradingView ───────────────────────────────────────────────
    tradingview_webhook_secret: str = "change-me"

    # ── Risk ──────────────────────────────────────────────────────
    risk_max_open_trades: int = 1
    risk_max_loss_pct: float = 20.0
    risk_risk_per_trade_pct: float = 1.0
    risk_allow_opposite_sides: bool = False

    # ── Logging ───────────────────────────────────────────────────
    log_level: str = "INFO"
    log_dir: str = Field(default_factory=lambda: str(PROJECT_ROOT / "logs"))

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
