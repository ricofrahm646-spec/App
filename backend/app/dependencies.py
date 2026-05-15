from pathlib import Path

from app.core.config import get_settings
from app.services.backtesting_service import BacktestingService
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.file_generator import FileGenerator
from app.services.mql5_generator import MQL5Generator
from app.services.mt5_connector import MT5Gateway, build_mt5_connector
from app.services.mt5_installer import MT5Installer
from app.services.risk_engine import RiskEngine
from app.services.strategy_registry import StrategyRegistry
from app.services.telegram_service import TelegramService
from app.services.tradingview_service import TradingViewService


settings = get_settings()

chat_orchestrator = ChatOrchestrator()
risk_engine = RiskEngine()
mt5_connector: MT5Gateway = build_mt5_connector()
backtesting_service = BacktestingService()
strategy_registry = StrategyRegistry()
mql5_generator = MQL5Generator(base_dir=Path("mql5/generated"))
mt5_installer = MT5Installer(mt5_data_path=Path(settings.mt5_data_path))
telegram_service = TelegramService(token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id)
tradingview_service = TradingViewService()
file_generator = FileGenerator(base_dir=Path("."))
