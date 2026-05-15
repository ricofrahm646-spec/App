from fastapi import APIRouter

from app.api.routes import backtesting, chat, files, health, mql5, risk, strategies, telegram, trading, tradingview

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(backtesting.router, prefix="/backtesting", tags=["backtesting"])
api_router.include_router(mql5.router, prefix="/mql5", tags=["mql5"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(tradingview.router, prefix="/tradingview", tags=["tradingview"])
