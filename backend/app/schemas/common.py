"""Shared Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AccountSnapshot(BaseModel):
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    profit: float = 0.0
    currency: str = "USD"
    leverage: int = 100
    server: str | None = None


class TradeRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    volume: float = Field(gt=0)
    sl: float | None = None
    tp: float | None = None
    comment: str | None = "jarvis"
    strategy_id: int | None = None


class TradeView(BaseModel):
    ticket: int | None = None
    symbol: str
    side: Literal["BUY", "SELL"]
    volume: float
    entry_price: float
    exit_price: float | None = None
    sl: float | None = None
    tp: float | None = None
    profit: float = 0.0
    status: str = "open"
    opened_at: datetime
    closed_at: datetime | None = None


class StrategyView(BaseModel):
    id: int | None = None
    name: str
    kind: str
    symbol: str
    timeframe: str
    parameters: dict[str, Any] = {}
    enabled: bool = True
    score: float = 0.0
    notes: str = ""


class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    intent: str | None = None
    meta: dict[str, Any] = {}
