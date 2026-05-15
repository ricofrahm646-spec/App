from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/tradingview", tags=["TradingView"])

@router.post("/webhook")
async def tradingview_webhook(request: Request):
    try:
        data = await request.json()
        print(f"Received TradingView Alert: {data}")
        # Logic to convert alert to MT5 Order
        return {"status": "success", "message": "Alert processed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid TradingView payload")

@router.get("/config")
async def get_tv_config():
    return {
        "webhook_url": "https://jarvis.ai/api/tradingview/webhook",
        "supported_pairs": ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]
    }
