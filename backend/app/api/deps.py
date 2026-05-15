"""
FastAPI dependency providers for singleton service instances.
"""
from app.services.mt5_service import MT5Service
from app.services.ai_service import AIService
from app.services.telegram_service import TelegramService
from app.services.tradingview_service import TradingViewService

# Module-level singletons (one instance per process)
_mt5 = MT5Service()
_ai = AIService()
_telegram = TelegramService()
_tv = TradingViewService()


def get_mt5() -> MT5Service:
    return _mt5


def get_ai() -> AIService:
    return _ai


def get_telegram() -> TelegramService:
    return _telegram


def get_tv() -> TradingViewService:
    return _tv
