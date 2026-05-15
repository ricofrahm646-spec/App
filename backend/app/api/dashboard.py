from fastapi import APIRouter, Depends

from ai.learning import LearningStack
from backend.app.dependencies import get_learning_stack, get_mt5_connector, get_strategy_registry
from backend.app.schemas import AccountSnapshot
from mt5.connector import MT5Connector
from strategies.registry import StrategyRegistry

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def summary(
    connector: MT5Connector = Depends(get_mt5_connector),
    registry: StrategyRegistry = Depends(get_strategy_registry),
    learning_stack: LearningStack = Depends(get_learning_stack),
) -> dict:
    account = connector.account_snapshot()
    positions = connector.list_open_positions()
    return {
        "account": AccountSnapshot(
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.free_margin,
            drawdown_percent=max(0, (account.balance - account.equity) / account.balance * 100)
            if account.balance
            else 0,
            currency=account.currency,
        ),
        "metrics": {
            "winrate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "profit_factor": 0.0,
            "drawdown": 0.0,
        },
        "ai_status": [capability.__dict__ for capability in learning_stack.capabilities()],
        "strategy_status": [strategy.model_dump() for strategy in registry.list_strategies()],
        "open_trades": [position.__dict__ for position in positions],
        "closed_trades": [],
        "live_market_analysis": {
            "phase": learning_stack.detect_market_phase({"volatility": 0.35, "trend_strength": 0.45}),
            "notes": ["Connect broker tick feed for production live analysis."],
        },
    }
