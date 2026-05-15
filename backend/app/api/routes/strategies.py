from fastapi import APIRouter

from app.dependencies import strategy_registry
from app.models.strategy import StrategyDefinition, StrategyScore

router = APIRouter()


@router.get("/", response_model=list[StrategyDefinition])
def list_strategies() -> list[StrategyDefinition]:
    return strategy_registry.list_all()


@router.post("/", response_model=StrategyDefinition)
def upsert_strategy(payload: StrategyDefinition) -> StrategyDefinition:
    return strategy_registry.upsert(payload)


@router.get("/evaluate", response_model=list[StrategyScore])
def evaluate_strategies() -> list[StrategyScore]:
    return strategy_registry.evaluate()
