from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, PositiveFloat, computed_field


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class StrategyType(StrEnum):
    SCALPING = "scalping"
    ICT = "ict"
    SMART_MONEY = "smart_money"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    ORDERBLOCK = "orderblock"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    SESSION = "session"


class AccountState(BaseModel):
    balance: PositiveFloat
    equity: PositiveFloat
    margin: float = Field(ge=0)
    free_margin: float = Field(ge=0)
    open_trades: int = Field(ge=0)

    @computed_field
    @property
    def drawdown_percent(self) -> float:
        if self.balance <= 0:
            return 0.0
        return max(0.0, (self.balance - self.equity) / self.balance * 100)


class TradeRequest(BaseModel):
    symbol: str = Field(min_length=3, examples=["XAUUSD", "EURUSD"])
    side: TradeSide
    entry_price: PositiveFloat
    stop_loss: PositiveFloat
    take_profit: PositiveFloat
    risk_percent: float = Field(default=1.0, gt=0, le=5)
    strategy_id: str


class OpenTrade(BaseModel):
    ticket: str
    symbol: str
    side: TradeSide
    volume: PositiveFloat
    entry_price: PositiveFloat
    current_price: PositiveFloat
    stop_loss: PositiveFloat
    take_profit: PositiveFloat
    opened_at: datetime
    floating_pl: float


class RiskDecision(BaseModel):
    allowed: bool
    reason: str
    lot_size: float = 0.0
    emergency_close: bool = False
    actions: list[str] = Field(default_factory=list)


class StrategySpec(BaseModel):
    name: str
    strategy_type: StrategyType
    symbols: list[str]
    timeframes: list[str]
    description: str
    risk_percent: float = Field(default=1.0, gt=0, le=5)
    parameters: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    context: list[ChatMessage] = Field(default_factory=list)


class GeneratedFile(BaseModel):
    path: str
    language: str
    purpose: str
    content: str


class ChatResponse(BaseModel):
    answer: str
    intent: str
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class BacktestRequest(BaseModel):
    strategy: StrategySpec
    initial_cash: PositiveFloat = 10_000
    spread_points: float = Field(default=10, ge=0)
    slippage_points: float = Field(default=2, ge=0)
    timeframe: str = "M5"
    data: list[dict[str, Any]] = Field(default_factory=list)


class BacktestResult(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    profit_factor: float
    max_drawdown_percent: float
    net_profit: float
    warnings: list[str] = Field(default_factory=list)


class DashboardSnapshot(BaseModel):
    balance: float
    equity: float
    margin: float
    winrate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    profit_factor: float
    drawdown: float
    ai_status: str
    strategy_status: str
    open_trades: list[OpenTrade] = Field(default_factory=list)
    closed_trades: list[dict[str, Any]] = Field(default_factory=list)
    live_market_analysis: dict[str, Any] = Field(default_factory=dict)
