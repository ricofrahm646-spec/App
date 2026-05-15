from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    buy = "buy"
    sell = "sell"


class ChatRequest(BaseModel):
    command: str = Field(min_length=2, max_length=500)
    context: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    summary: str
    actions: list[str] = Field(default_factory=list)
    generated_files: list[str] = Field(default_factory=list)


class TradeRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=20)
    side: TradeSide
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=2.0)


class TradeState(BaseModel):
    is_open: bool
    symbol: str | None = None
    side: TradeSide | None = None
    entry_price: float | None = None
    unrealized_pnl_pct: float = 0.0
    opened_at: datetime | None = None


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    max_loss_threshold_pct: float = 20.0


class BacktestRequest(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    walk_forward: bool = True
    monte_carlo_runs: int = Field(default=100, ge=10, le=5000)


class BacktestResult(BaseModel):
    strategy_name: str
    symbol: str
    winrate: float
    profit_factor: float
    max_drawdown: float
    notes: list[str] = Field(default_factory=list)
