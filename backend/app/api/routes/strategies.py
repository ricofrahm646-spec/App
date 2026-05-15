from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    APIResponse,
    PaginatedResponse,
    StrategyCreate,
    StrategyResponse,
    StrategyStatus,
    StrategyUpdate,
)

logger = structlog.get_logger("jarvis.strategies")
router = APIRouter(prefix="/strategies", tags=["Strategies"])

_strategies: dict[str, StrategyResponse] = {}


@router.get(
    "",
    response_model=APIResponse,
    summary="List all strategies",
)
async def list_strategies(
    status_filter: StrategyStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> APIResponse:
    items = list(_strategies.values())
    if status_filter:
        items = [s for s in items if s.status == status_filter]

    total = len(items)
    start = (page - 1) * page_size
    paginated = items[start : start + page_size]

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[s.model_dump(mode="json") for s in paginated],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        ).model_dump(mode="json"),
    )


@router.get(
    "/{strategy_id}",
    response_model=APIResponse,
    summary="Get strategy by ID",
)
async def get_strategy(strategy_id: str) -> APIResponse:
    strategy = _strategies.get(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found.",
        )
    return APIResponse(success=True, data=strategy.model_dump(mode="json"))


@router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new strategy",
)
async def create_strategy(request: StrategyCreate) -> APIResponse:
    for s in _strategies.values():
        if s.name.lower() == request.name.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Strategy with name '{request.name}' already exists.",
            )

    now = datetime.now(timezone.utc)
    strategy = StrategyResponse(
        id=uuid.uuid4().hex[:12],
        name=request.name,
        description=request.description,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        parameters=request.parameters,
        entry_rules=request.entry_rules,
        exit_rules=request.exit_rules,
        risk_per_trade=request.risk_per_trade,
        max_positions=request.max_positions,
        status=StrategyStatus.INACTIVE,
        created_at=now,
        updated_at=now,
    )
    _strategies[strategy.id] = strategy

    logger.info("strategy_created", id=strategy.id, name=strategy.name)
    return APIResponse(
        success=True,
        message="Strategy created.",
        data=strategy.model_dump(mode="json"),
    )


@router.put(
    "/{strategy_id}",
    response_model=APIResponse,
    summary="Update an existing strategy",
)
async def update_strategy(strategy_id: str, request: StrategyUpdate) -> APIResponse:
    strategy = _strategies.get(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found.",
        )

    if strategy.status == StrategyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deactivate the strategy before updating.",
        )

    updates = request.model_dump(exclude_none=True)
    if "symbol" in updates:
        updates["symbol"] = updates["symbol"].upper()
    updates["updated_at"] = datetime.now(timezone.utc)

    _strategies[strategy_id] = strategy.model_copy(update=updates)
    logger.info("strategy_updated", id=strategy_id)
    return APIResponse(
        success=True,
        message="Strategy updated.",
        data=_strategies[strategy_id].model_dump(mode="json"),
    )


@router.delete(
    "/{strategy_id}",
    response_model=APIResponse,
    summary="Delete a strategy",
)
async def delete_strategy(strategy_id: str) -> APIResponse:
    strategy = _strategies.pop(strategy_id, None)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found.",
        )
    if strategy.status == StrategyStatus.ACTIVE:
        _strategies[strategy_id] = strategy
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active strategy. Deactivate it first.",
        )

    logger.info("strategy_deleted", id=strategy_id, name=strategy.name)
    return APIResponse(success=True, message=f"Strategy '{strategy.name}' deleted.")


@router.post(
    "/{strategy_id}/activate",
    response_model=APIResponse,
    summary="Activate a strategy for live trading",
)
async def activate_strategy(strategy_id: str) -> APIResponse:
    strategy = _strategies.get(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found.",
        )
    if strategy.status == StrategyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already active.",
        )

    if not strategy.entry_rules or not strategy.exit_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy must have entry and exit rules before activation.",
        )

    _strategies[strategy_id] = strategy.model_copy(
        update={
            "status": StrategyStatus.ACTIVE,
            "updated_at": datetime.now(timezone.utc),
        }
    )
    logger.info("strategy_activated", id=strategy_id)
    return APIResponse(success=True, message=f"Strategy '{strategy.name}' activated.")


@router.post(
    "/{strategy_id}/deactivate",
    response_model=APIResponse,
    summary="Deactivate a strategy",
)
async def deactivate_strategy(strategy_id: str) -> APIResponse:
    strategy = _strategies.get(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found.",
        )
    if strategy.status == StrategyStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is already inactive.",
        )

    _strategies[strategy_id] = strategy.model_copy(
        update={
            "status": StrategyStatus.INACTIVE,
            "updated_at": datetime.now(timezone.utc),
        }
    )
    logger.info("strategy_deactivated", id=strategy_id)
    return APIResponse(success=True, message=f"Strategy '{strategy.name}' deactivated.")
