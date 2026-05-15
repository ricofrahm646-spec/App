from fastapi import APIRouter

from app.services.orchestrator import JarvisOrchestrator

router = APIRouter()
orchestrator = JarvisOrchestrator()


@router.post("/tradingview/webhook")
def tradingview_webhook(payload: dict[str, str | float]) -> dict[str, str]:
    signal = orchestrator.tradingview.parse_webhook(payload)
    return {
        "status": "accepted",
        "symbol": signal.symbol,
        "side": signal.side,
        "source": signal.source,
    }


@router.post("/telegram/test")
async def telegram_test() -> dict[str, str]:
    sent = await orchestrator.telegram.send_message("JARVIS test notification.")
    return {"status": "sent" if sent else "skipped"}
