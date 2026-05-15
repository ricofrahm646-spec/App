"""
Strategies Router - CRUD, activation, performance, and evaluation of trading strategies.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.strategy import Strategy, StrategyStatus, StrategyType
from app.services.strategy_service import StrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


# ─────────────────────────────────────── Request / Response models ────────────

class CreateStrategyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(StrategyType.CUSTOM, description="Strategy type")
    description: Optional[str] = Field(None)
    config: Dict[str, Any] = Field(default={}, description="Strategy configuration parameters")
    source_code: Optional[str] = Field(None, description="Strategy source code")
    is_ai_generated: bool = Field(False)


class UpdateStrategyRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    source_code: Optional[str] = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    type: str
    status: str
    description: Optional[str]
    config: Dict[str, Any]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    is_ai_generated: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, s: Strategy) -> "StrategyResponse":
        return cls(
            id=s.id,
            name=s.name,
            type=s.type.value if hasattr(s.type, "value") else str(s.type),
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
            description=s.description,
            config=s.config or {},
            total_trades=s.total_trades or 0,
            winning_trades=s.winning_trades or 0,
            losing_trades=s.losing_trades or 0,
            win_rate=s.win_rate or 0.0,
            profit_factor=s.profit_factor or 0.0,
            max_drawdown=s.max_drawdown or 0.0,
            sharpe_ratio=s.sharpe_ratio or 0.0,
            is_ai_generated=s.is_ai_generated or False,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else "",
        )


# ─────────────────────────────────────────────────────── Endpoints ────────────

@router.get("", summary="List all strategies")
def list_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all strategies with optional status filter and pagination."""
    status_enum = None
    if status_filter:
        try:
            status_enum = StrategyStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status_filter}'. Valid values: {[s.value for s in StrategyStatus]}",
            )
    strategies = StrategyService.list_strategies(db, skip=skip, limit=limit, status=status_enum)
    return [StrategyResponse.from_orm_model(s).model_dump() for s in strategies]


@router.post("", summary="Create new strategy", status_code=status.HTTP_201_CREATED)
def create_strategy(req: CreateStrategyRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Create a new strategy record."""
    existing = db.query(Strategy).filter(Strategy.name == req.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Strategy with name '{req.name}' already exists (id={existing.id})",
        )
    strategy = StrategyService.create_strategy(db, req.model_dump())
    return StrategyResponse.from_orm_model(strategy).model_dump()


@router.get("/active", summary="Get active strategies")
def get_active_strategies(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return only strategies with ACTIVE status."""
    strategies = StrategyService.get_active_strategies(db)
    return [StrategyResponse.from_orm_model(s).model_dump() for s in strategies]


@router.post("/evaluate", summary="Evaluate and rank all strategies")
def evaluate_strategies(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Score every strategy using a composite performance metric and return them ranked.
    Factors: win rate (30%), profit factor (20%), Sharpe (20%), drawdown penalty (5%), trade count (bonus).
    """
    return StrategyService.evaluate_and_rank(db)


@router.get("/{strategy_id}", summary="Get strategy details")
def get_strategy(strategy_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return full details of a single strategy including source code."""
    strategy = StrategyService.get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")
    data = StrategyResponse.from_orm_model(strategy).model_dump()
    data["source_code"] = strategy.source_code
    data["ai_model_used"] = strategy.ai_model_used
    data["activated_at"] = strategy.activated_at.isoformat() if strategy.activated_at else None
    data["last_trade_at"] = strategy.last_trade_at.isoformat() if strategy.last_trade_at else None
    return data


@router.put("/{strategy_id}", summary="Update strategy")
def update_strategy(
    strategy_id: int,
    req: UpdateStrategyRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update mutable fields of a strategy (name, description, config, source code)."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    strategy = StrategyService.update_strategy(db, strategy_id, updates)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")
    return StrategyResponse.from_orm_model(strategy).model_dump()


@router.delete("/{strategy_id}", summary="Delete strategy")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Permanently delete a strategy record."""
    deleted = StrategyService.delete_strategy(db, strategy_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")
    return {"deleted": True, "strategy_id": strategy_id}


@router.post("/{strategy_id}/activate", summary="Activate strategy")
def activate_strategy(strategy_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Set strategy status to ACTIVE so it will be used in live trading."""
    strategy = StrategyService.activate_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")
    return {
        "activated": True,
        "strategy_id": strategy_id,
        "status": strategy.status.value,
        "activated_at": strategy.activated_at.isoformat() if strategy.activated_at else None,
    }


@router.post("/{strategy_id}/deactivate", summary="Deactivate strategy")
def deactivate_strategy(strategy_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Set strategy status to INACTIVE."""
    strategy = StrategyService.deactivate_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")
    return {
        "deactivated": True,
        "strategy_id": strategy_id,
        "status": strategy.status.value,
    }


@router.get("/{strategy_id}/performance", summary="Strategy performance metrics")
def get_performance(strategy_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return detailed performance metrics for a strategy."""
    strategy = StrategyService.get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy #{strategy_id} not found")
    return StrategyService.get_performance_metrics(db, strategy_id)
