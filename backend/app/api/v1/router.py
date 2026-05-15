"""API v1 routers."""

from fastapi import APIRouter

from app.api.v1 import backtest, chat, health, mt5 as mt5_routes, risk, telegram, tradingview

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(mt5_routes.router, prefix="/mt5", tags=["mt5"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(tradingview.router, prefix="/tradingview", tags=["tradingview"])
