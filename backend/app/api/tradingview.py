from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_tradingview_handler
from backend.app.schemas import TradingViewWebhook
from tradingview.pine_script import forex_signal_strategy
from tradingview.webhooks import TradingViewWebhookHandler

router = APIRouter(prefix="/tradingview", tags=["TradingView"])


@router.get("/pine-script")
async def pine_script() -> dict[str, str]:
    return {"script": forex_signal_strategy()}


@router.post("/webhook")
async def webhook(
    payload: TradingViewWebhook,
    handler: TradingViewWebhookHandler = Depends(get_tradingview_handler),
) -> dict:
    valid, reason = handler.validate(payload)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)
    return {
        "accepted": True,
        "reason": reason,
        "signal": payload.model_dump(exclude={"secret"}),
    }
