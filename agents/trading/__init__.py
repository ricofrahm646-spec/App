"""Trading agent cluster for JARVIS AI OS."""

from agents.trading.arbitrage_bot import ArbitrageBotAgent
from agents.trading.gold_scalper_pro import GoldScalperProAgent
from agents.trading.liquidity_sweeper import LiquiditySweeperAgent
from agents.trading.news_reactor import NewsReactorAgent
from agents.trading.orderflow_master import OrderflowMasterAgent
from agents.trading.portfolio_allocator import PortfolioAllocatorAgent
from agents.trading.risk_commander import RiskCommanderAgent
from agents.trading.session_sniper import SessionSniperAgent
from agents.trading.trend_pulse_ai import TrendPulseAIAgent
from agents.trading.volatility_guardian import VolatilityGuardianAgent

__all__ = [
    "GoldScalperProAgent",
    "RiskCommanderAgent",
    "LiquiditySweeperAgent",
    "NewsReactorAgent",
    "OrderflowMasterAgent",
    "ArbitrageBotAgent",
    "SessionSniperAgent",
    "VolatilityGuardianAgent",
    "TrendPulseAIAgent",
    "PortfolioAllocatorAgent",
]

