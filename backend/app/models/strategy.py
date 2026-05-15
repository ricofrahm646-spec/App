from pydantic import BaseModel, Field


class StrategyDefinition(BaseModel):
    strategy_id: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    style: str = Field(..., min_length=2)
    enabled: bool = True
    parameters: dict[str, float | int | str | bool] = Field(default_factory=dict)


class StrategyScore(BaseModel):
    strategy_id: str
    score: float
    reason: str
