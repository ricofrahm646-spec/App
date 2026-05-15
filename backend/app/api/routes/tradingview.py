from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import get_settings
from app.dependencies import tradingview_service

router = APIRouter()
settings = get_settings()


@router.post("/webhook")
async def tradingview_webhook(
    request: Request,
    x_signature: str = Header(default="", alias="X-Signature"),
) -> dict[str, str]:
    body = await request.body()
    valid = tradingview_service.validate_webhook_signature(
        body=body,
        provided_secret=x_signature,
        expected_secret=settings.tradingview_webhook_secret,
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid TradingView webhook signature")

    # In production this payload feeds the strategy/risk/trading pipelines.
    return {"status": "received"}
