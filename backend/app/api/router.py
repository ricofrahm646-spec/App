"""Aggregate API router."""
from fastapi import APIRouter

from backend.app.api.routes import (
    account,
    backtest,
    chat,
    mql5 as mql5_routes,
    strategies,
    system,
    telegram as telegram_routes,
    trades,
    tradingview,
    websocket,
)

api_router = APIRouter()
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(mql5_routes.router, prefix="/mql5", tags=["mql5"])
api_router.include_router(telegram_routes.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(tradingview.router, prefix="/tradingview", tags=["tradingview"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(websocket.router, tags=["websocket"])
