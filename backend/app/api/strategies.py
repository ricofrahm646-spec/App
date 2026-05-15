from fastapi import APIRouter, Depends

from backend.app.dependencies import get_strategy_registry
from backend.app.schemas import StrategySpec
from strategies.registry import StrategyRegistry

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("/archetypes")
async def archetypes(registry: StrategyRegistry = Depends(get_strategy_registry)) -> list[str]:
    return registry.list_supported_archetypes()


@router.get("", response_model=list[StrategySpec])
async def list_strategies(registry: StrategyRegistry = Depends(get_strategy_registry)) -> list[StrategySpec]:
    return registry.list_strategies()


@router.post("", response_model=StrategySpec)
async def create_strategy(
    spec: StrategySpec,
    registry: StrategyRegistry = Depends(get_strategy_registry),
) -> StrategySpec:
    return registry.register(spec)
