from typing import Literal

from pydantic import BaseModel, Field


class ChatCommandRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    symbol: str | None = None
    timeframe: str | None = None


class GeneratedArtifact(BaseModel):
    path: str
    purpose: str
    language: str


class CommandAction(BaseModel):
    kind: Literal["strategy", "risk", "indicator", "integration", "optimization"]
    description: str


class ChatCommandResponse(BaseModel):
    summary: str
    actions: list[CommandAction]
    artifacts: list[GeneratedArtifact]
    warnings: list[str]


class TradeGuardrailSnapshot(BaseModel):
    max_live_trades: int
    allow_hedging: bool
    force_close_loss_percent: float
    status: Literal["armed", "halted"]


class SystemOverview(BaseModel):
    balance: float
    equity: float
    margin: float
    win_rate: float
    drawdown: float
    open_trades: int
    closed_trades: int
    ai_status: str
    strategy_status: str
    risk: TradeGuardrailSnapshot
