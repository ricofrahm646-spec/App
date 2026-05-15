from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeRequest(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=20)
    side: TradeSide
    volume: float = Field(..., gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    strategy_id: str = Field(..., min_length=2)


class TradePosition(BaseModel):
    ticket: int
    symbol: str
    side: TradeSide
    volume: float
    entry_price: float
    current_price: float
    pnl_percent: float
    status: Literal["open", "closed"] = "open"


class CloseTradeRequest(BaseModel):
    ticket: int


class RiskSnapshot(BaseModel):
    equity: float = Field(..., ge=0)
    margin: float = Field(..., ge=0)
    drawdown_percent: float = Field(..., ge=0)
    max_drawdown_percent: float = Field(default=20.0, gt=0)

    @field_validator("drawdown_percent")
    @classmethod
    def drawdown_bounds(cls, value: float) -> float:
        if value > 100:
            raise ValueError("drawdown_percent must be <= 100")
        return value
