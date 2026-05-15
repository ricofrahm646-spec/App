from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatCommandRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1_000)


class GeneratedArtifact(BaseModel):
    path: str
    kind: Literal["python", "mql5", "markdown", "json", "yaml"]
    summary: str


class ActionPlan(BaseModel):
    title: str
    description: str
    actions: list[str]
    generated_artifacts: list[GeneratedArtifact] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class ChatCommandResponse(BaseModel):
    intent: str
    acknowledgement: str
    plan: ActionPlan
    created_files: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MetricCard(BaseModel):
    label: str
    value: str
    detail: str


class ModuleStatus(BaseModel):
    name: str
    status: Literal["healthy", "degraded", "pending"]
    description: str


class TradeSnapshot(BaseModel):
    symbol: str
    direction: Literal["buy", "sell"]
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy: str
    state: Literal["open", "closed", "draft"]


class SystemOverview(BaseModel):
    metrics: list[MetricCard]
    modules: list[ModuleStatus]
    open_trades: list[TradeSnapshot]
    active_strategy: str
    ai_status: str
