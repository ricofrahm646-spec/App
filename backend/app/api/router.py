from fastapi import APIRouter

from app.api.routes import backtesting, chat, health, integrations, risk, trading

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(backtesting.router, prefix="/backtesting", tags=["backtesting"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
