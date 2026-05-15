from functools import lru_cache

from ai.chat_orchestrator import ChatOrchestrator
from ai.learning import LearningStack
from backend.app.config import get_settings
from backtesting.engine import BacktestEngine
from mql5.generator import MQL5Generator
from mt5.connector import MT5Connector
from mt5.installer import MT5Installer
from risk_management.engine import RiskEngine
from strategies.registry import StrategyRegistry
from telegram.client import TelegramConfig, TelegramNotifier
from tradingview.webhooks import TradingViewWebhookHandler


@lru_cache
def get_risk_engine() -> RiskEngine:
    settings = get_settings()
    return RiskEngine(
        max_open_trades=settings.max_open_trades,
        forced_close_loss_percent=settings.forced_close_loss_percent,
    )


@lru_cache
def get_strategy_registry() -> StrategyRegistry:
    return StrategyRegistry()


@lru_cache
def get_mql5_generator() -> MQL5Generator:
    return MQL5Generator()


@lru_cache
def get_chat_orchestrator() -> ChatOrchestrator:
    return ChatOrchestrator(get_strategy_registry(), get_mql5_generator())


@lru_cache
def get_mt5_connector() -> MT5Connector:
    return MT5Connector(get_settings(), get_risk_engine())


@lru_cache
def get_mt5_installer() -> MT5Installer:
    settings = get_settings()
    return MT5Installer(data_path=settings.mt5_data_path)


@lru_cache
def get_backtest_engine() -> BacktestEngine:
    return BacktestEngine()


@lru_cache
def get_learning_stack() -> LearningStack:
    return LearningStack()


@lru_cache
def get_telegram_notifier() -> TelegramNotifier:
    settings = get_settings()
    return TelegramNotifier(TelegramConfig(settings.telegram_bot_token, settings.telegram_chat_id))


@lru_cache
def get_tradingview_handler() -> TradingViewWebhookHandler:
    return TradingViewWebhookHandler(get_settings().tradingview_webhook_secret)
