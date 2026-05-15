from fastapi import APIRouter, WebSocket

from app.models.schemas import ChatCommandRequest, SystemOverview, TradeGuardrailSnapshot
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.risk_engine import RiskEngine

router = APIRouter()
chat = ChatOrchestrator()
risk = RiskEngine()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "jarvis-api"}


@router.get("/system/overview", response_model=SystemOverview)
def system_overview() -> SystemOverview:
    return SystemOverview(
        balance=10_000.0,
        equity=10_120.0,
        margin=245.0,
        win_rate=0.58,
        drawdown=0.08,
        open_trades=1,
        closed_trades=42,
        ai_status="ready",
        strategy_status="monitoring",
        risk=TradeGuardrailSnapshot(
            max_live_trades=risk.max_live_trades,
            allow_hedging=risk.allow_hedging,
            force_close_loss_percent=risk.force_close_loss_percent,
            status="armed",
        ),
    )


@router.post("/chat/command")
def handle_command(payload: ChatCommandRequest):
    return chat.handle(payload.prompt)


@router.websocket("/ws/system")
async def system_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "system.snapshot",
            "payload": {
                "balance": 10_000,
                "equity": 10_120,
                "drawdown": 0.08,
                "strategy_status": "monitoring",
                "ai_status": "ready",
            },
        }
    )
    await websocket.close()
