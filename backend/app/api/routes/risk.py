from fastapi import APIRouter

from app.models.schemas import RiskDecision
from app.services.orchestrator import JarvisOrchestrator

router = APIRouter()
orchestrator = JarvisOrchestrator()


@router.get("/policy", response_model=RiskDecision)
def get_policy() -> RiskDecision:
    return RiskDecision(
        approved=True,
        reason="Risk policy loaded.",
        max_loss_threshold_pct=orchestrator.risk_engine.max_loss_threshold_pct,
    )


@router.get("/force-close-check")
def force_close_check() -> dict[str, bool]:
    state = orchestrator.mt5.get_trade_state()
    should_close = orchestrator.risk_engine.should_force_close(state)
    return {"should_force_close": should_close}
