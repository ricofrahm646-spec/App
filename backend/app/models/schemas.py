from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════════
# Generic wrappers
# ═══════════════════════════════════════════════════════════════════════════

class APIResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    items: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TimeFrame(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


class StrategyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class BacktestStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationType(str, Enum):
    TRADE = "TRADE"
    ERROR = "ERROR"
    INFO = "INFO"
    DAILY_SUMMARY = "DAILY_SUMMARY"


# ═══════════════════════════════════════════════════════════════════════════
# Trading
# ═══════════════════════════════════════════════════════════════════════════

class TradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, examples=["EURUSD"])
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    volume: float = Field(..., gt=0, le=100.0, examples=[0.1])
    price: float | None = Field(default=None, ge=0)
    stop_loss: float | None = Field(default=None, ge=0)
    take_profit: float | None = Field(default=None, ge=0)
    deviation: int = Field(default=20, ge=0, le=100)
    magic_number: int = Field(default=123456)
    comment: str = Field(default="JARVIS", max_length=63)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper().strip()


class CloseTradeRequest(BaseModel):
    ticket: int = Field(..., gt=0)
    volume: float | None = Field(default=None, gt=0, le=100.0)
    deviation: int = Field(default=20, ge=0, le=100)


class ModifyTradeRequest(BaseModel):
    ticket: int = Field(..., gt=0)
    stop_loss: float | None = Field(default=None, ge=0)
    take_profit: float | None = Field(default=None, ge=0)


class TradeResponse(BaseModel):
    ticket: int
    symbol: str
    side: OrderSide
    order_type: OrderType
    volume: float
    open_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    open_time: datetime
    close_time: datetime | None = None
    close_price: float | None = None
    magic_number: int = 0
    comment: str = ""
    status: OrderStatus = OrderStatus.FILLED


class PositionResponse(BaseModel):
    ticket: int
    symbol: str
    side: OrderSide
    volume: float
    open_price: float
    current_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    open_time: datetime
    magic_number: int = 0
    comment: str = ""


class AccountInfo(BaseModel):
    login: int = 0
    name: str = ""
    server: str = ""
    currency: str = "USD"
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    leverage: int = 100
    profit: float = 0.0
    connected: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# Strategies
# ═══════════════════════════════════════════════════════════════════════════

class StrategyParameter(BaseModel):
    name: str
    value: Any
    param_type: str = "float"
    min_value: Any | None = None
    max_value: Any | None = None
    description: str = ""


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframe: TimeFrame = TimeFrame.H1
    parameters: list[StrategyParameter] = []
    entry_rules: str = Field(default="", max_length=5000)
    exit_rules: str = Field(default="", max_length=5000)
    risk_per_trade: float = Field(default=1.0, gt=0, le=100)
    max_positions: int = Field(default=1, ge=1, le=100)


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    symbol: str | None = Field(default=None, min_length=1, max_length=20)
    timeframe: TimeFrame | None = None
    parameters: list[StrategyParameter] | None = None
    entry_rules: str | None = Field(default=None, max_length=5000)
    exit_rules: str | None = Field(default=None, max_length=5000)
    risk_per_trade: float | None = Field(default=None, gt=0, le=100)
    max_positions: int | None = Field(default=None, ge=1, le=100)


class StrategyResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    symbol: str
    timeframe: TimeFrame
    parameters: list[StrategyParameter] = []
    entry_rules: str = ""
    exit_rules: str = ""
    risk_per_trade: float = 1.0
    max_positions: int = 1
    status: StrategyStatus = StrategyStatus.INACTIVE
    total_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Backtesting
# ═══════════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframe: TimeFrame = TimeFrame.H1
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000.0, gt=0)
    commission: float = Field(default=0.0002, ge=0)
    spread: float = Field(default=0.0, ge=0)
    parameters: dict[str, Any] = {}

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info: Any) -> datetime:
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v


class WalkForwardRequest(BaseModel):
    strategy_id: str
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframe: TimeFrame = TimeFrame.H1
    start_date: datetime
    end_date: datetime
    in_sample_ratio: float = Field(default=0.7, gt=0, lt=1)
    num_folds: int = Field(default=5, ge=2, le=20)
    initial_capital: float = Field(default=10000.0, gt=0)
    parameters: dict[str, Any] = {}


class MonteCarloRequest(BaseModel):
    backtest_id: str
    num_simulations: int = Field(default=1000, ge=100, le=100000)
    confidence_level: float = Field(default=0.95, gt=0, lt=1)


class BacktestTradeResult(BaseModel):
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: OrderSide
    volume: float
    entry_price: float
    exit_price: float
    profit: float
    commission: float = 0.0
    duration_minutes: int = 0


class BacktestMetrics(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    avg_trade_profit: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_holding_time_minutes: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    expectancy: float = 0.0
    recovery_factor: float = 0.0
    final_capital: float = 0.0


class BacktestResponse(BaseModel):
    id: str
    strategy_id: str
    symbol: str
    timeframe: TimeFrame
    start_date: datetime
    end_date: datetime
    status: BacktestStatus = BacktestStatus.QUEUED
    metrics: BacktestMetrics | None = None
    equity_curve: list[float] = []
    trades: list[BacktestTradeResult] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
    error_message: str | None = None


class WalkForwardResult(BaseModel):
    id: str
    folds: list[BacktestResponse] = []
    combined_metrics: BacktestMetrics | None = None
    robustness_score: float = 0.0


class MonteCarloResult(BaseModel):
    id: str
    backtest_id: str
    num_simulations: int
    confidence_level: float
    median_final_equity: float = 0.0
    worst_case_equity: float = 0.0
    best_case_equity: float = 0.0
    probability_of_ruin: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    equity_percentiles: dict[str, float] = {}


# ═══════════════════════════════════════════════════════════════════════════
# AI Chat
# ═══════════════════════════════════════════════════════════════════════════

class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    context: dict[str, Any] = {}
    stream: bool = False


class ChatMessage(BaseModel):
    id: str = ""
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = {}


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage] = []
    total: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════

class PerformanceMetrics(BaseModel):
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    total_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    monthly_pnl_pct: float = 0.0
    total_pnl_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0


class DashboardData(BaseModel):
    account: AccountInfo = Field(default_factory=AccountInfo)
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    open_positions: list[PositionResponse] = []
    recent_trades: list[TradeResponse] = []
    active_strategies: list[StrategyResponse] = []
    equity_history: list[dict[str, Any]] = []
    pnl_by_symbol: dict[str, float] = {}
    pnl_by_day: list[dict[str, Any]] = []


class TradeHistoryQuery(BaseModel):
    symbol: str | None = None
    side: OrderSide | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


# ═══════════════════════════════════════════════════════════════════════════
# Telegram
# ═══════════════════════════════════════════════════════════════════════════

class TelegramConfig(BaseModel):
    bot_token: str = Field(..., min_length=1)
    chat_id: str = Field(..., min_length=1)


class TelegramNotificationSettings(BaseModel):
    enabled: bool = True
    trade_alerts: bool = True
    error_alerts: bool = True
    daily_summary: bool = True


class TelegramTestResponse(BaseModel):
    success: bool
    message: str
    bot_username: str | None = None


# ═══════════════════════════════════════════════════════════════════════════
# TradingView
# ═══════════════════════════════════════════════════════════════════════════

class TradingViewAlert(BaseModel):
    action: OrderSide
    symbol: str
    order_type: OrderType = OrderType.MARKET
    volume: float = Field(default=0.1, gt=0)
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    strategy_id: str | None = None
    message: str = ""
    timestamp: str = ""


class TradingViewAlertConfig(BaseModel):
    id: str = ""
    name: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=1, max_length=20)
    action_on_buy: str = "open_long"
    action_on_sell: str = "open_short"
    volume: float = Field(default=0.1, gt=0)
    auto_execute: bool = False
    enabled: bool = True


class TradingViewAlertLog(BaseModel):
    id: str
    alert: TradingViewAlert
    executed: bool = False
    execution_result: str = ""
    received_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# MQL5 Code Generation
# ═══════════════════════════════════════════════════════════════════════════

class MQL5Type(str, Enum):
    EA = "EA"
    INDICATOR = "INDICATOR"
    SCRIPT = "SCRIPT"


class MQL5GenerateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    mql_type: MQL5Type = MQL5Type.EA
    description: str = Field(default="", max_length=2000)
    strategy_id: str | None = None
    parameters: list[StrategyParameter] = []
    entry_rules: str = Field(default="", max_length=5000)
    exit_rules: str = Field(default="", max_length=5000)
    risk_management: str = Field(default="", max_length=2000)
    additional_instructions: str = Field(default="", max_length=5000)


class MQL5CompileRequest(BaseModel):
    code: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1, max_length=200)


class MQL5InstallRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    mql_type: MQL5Type = MQL5Type.EA


class MQL5GenerateResponse(BaseModel):
    filename: str
    code: str
    mql_type: MQL5Type
    warnings: list[str] = []


class MQL5CompileResponse(BaseModel):
    success: bool
    filename: str
    errors: list[str] = []
    warnings: list[str] = []


# ═══════════════════════════════════════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════════════════════════════════════

class MT5ConnectionSettings(BaseModel):
    host: str = "localhost"
    port: int = Field(default=8001, ge=1, le=65535)
    account: int = Field(default=0, ge=0)
    password: str = ""
    server: str = ""
    path: str = ""
    timeout: int = Field(default=30000, ge=1000, le=120000)


class GeneralSettings(BaseModel):
    app_name: str = "JARVIS Trading OS"
    theme: str = "dark"
    language: str = "en"
    timezone: str = "UTC"
    default_symbol: str = "EURUSD"
    default_timeframe: TimeFrame = TimeFrame.H1
    notifications_enabled: bool = True
    sound_enabled: bool = True
    auto_refresh_interval: int = Field(default=5, ge=1, le=60)


class AISettings(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = Field(default=4096, ge=256, le=128000)
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = ""


class AllSettings(BaseModel):
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    mt5: MT5ConnectionSettings = Field(default_factory=MT5ConnectionSettings)
    ai: AISettings = Field(default_factory=AISettings)
    telegram: TelegramNotificationSettings = Field(
        default_factory=TelegramNotificationSettings
    )


# ═══════════════════════════════════════════════════════════════════════════
# WebSocket
# ═══════════════════════════════════════════════════════════════════════════

class WSMessageType(str, Enum):
    ACCOUNT_UPDATE = "account_update"
    POSITION_UPDATE = "position_update"
    TRADE_EXECUTED = "trade_executed"
    STRATEGY_SIGNAL = "strategy_signal"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    AI_CHAT_CHUNK = "ai_chat_chunk"
    AI_CHAT_DONE = "ai_chat_done"
    ALERT_RECEIVED = "alert_received"


class WSMessage(BaseModel):
    type: WSMessageType
    data: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════

class HealthCheck(BaseModel):
    status: str = "ok"
    version: str = ""
    environment: str = ""
    uptime_seconds: float = 0.0
    services: dict[str, bool] = {}
