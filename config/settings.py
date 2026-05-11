"""
J.A.R.V.I.S. V300 - Central Configuration
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MT5Config:
    login: int = int(os.getenv("MT5_LOGIN", "0"))
    password: str = os.getenv("MT5_PASSWORD", "")
    server: str = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
    path: str = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    symbol: str = os.getenv("MT5_SYMBOL", "EURUSD")
    timeframe: str = "M1"
    magic_number: int = 300300
    max_spread: int = 20
    deviation: int = 10


@dataclass
class TradingConfig:
    initial_balance: float = 10.0
    risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 5.0
    max_concurrent_trades: int = 3
    min_confluence_score: float = 0.90
    trail_stop_atr_mult: float = 1.5
    take_profit_rr: float = 2.0
    news_protection_minutes: int = 15
    session_london_start: int = 8
    session_london_end: int = 17
    session_ny_start: int = 13
    session_ny_end: int = 22


@dataclass
class DashboardConfig:
    host: str = "0.0.0.0"
    port: int = 8501
    theme_bg: str = "#0a0a0f"
    theme_accent: str = "#00d4ff"
    theme_success: str = "#00ff88"
    theme_danger: str = "#ff3366"
    theme_warning: str = "#ffaa00"
    refresh_interval_sec: int = 2


@dataclass
class SecurityConfig:
    enable_code_audit: bool = True
    audit_severity_threshold: str = "MEDIUM"
    news_sources: list = field(default_factory=lambda: [
        "https://www.forexfactory.com/calendar",
        "https://www.investing.com/economic-calendar/",
    ])


@dataclass
class JarvisConfig:
    mt5: MT5Config = field(default_factory=MT5Config)
    trading: TradingConfig = field(default_factory=TradingConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    voice_enabled: bool = True
    log_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    apps_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apps")
    user_title: str = "Sir"
