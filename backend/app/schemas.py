from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    buy = "buy"
    sell = "sell"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    strategy_id: str | None = None
    dry_run: bool = True


class GeneratedFile(BaseModel):
    path: str
    language: str
    purpose: str
    content: str


class ChatResponse(BaseModel):
    intent: str
    summary: str
    actions: list[str]
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class AccountSnapshot(BaseModel):
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    drawdown_percent: float = 0.0
    currency: str = "USD"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TradeRequest(BaseModel):
    symbol: str
    side: TradeSide
    risk_percent: float = Field(default=0.5, ge=0.01, le=5.0)
    stop_loss_points: float = Field(gt=0)
    take_profit_points: float = Field(gt=0)
    comment: str = "JARVIS"


class TradeResponse(BaseModel):
    accepted: bool
    mode: Literal["paper", "live"]
    reason: str
    order_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class StrategySpec(BaseModel):
    name: str
    archetype: str
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    risk_profile: str = "conservative"


class BacktestRequest(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    initial_cash: float = 10_000
    spread_points: float = 10
    slippage_points: float = 2
    walk_forward_splits: int = 3
    monte_carlo_runs: int = 100


class BacktestResult(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    total_trades: int
    winrate: float
    profit_factor: float
    max_drawdown_percent: float
    notes: list[str]


class TelegramSettingsRequest(BaseModel):
    token: str = Field(min_length=10)
    chat_id: str = Field(min_length=1)


class TradingViewWebhook(BaseModel):
    secret: str
    symbol: str
    side: TradeSide
    price: float
    timeframe: str
    strategy: str
    stop_loss: float | None = None
    take_profit: float | None = None
