import pytest
import asyncio
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.gmail_architect import GmailArchitect

@pytest.mark.asyncio
async def test_trading_swarm():
    agent = TradingSwarm()
    result = await agent.process("trade gold")
    assert "QUANTUM_TRADE_INITIALIZED" in result["output"]

@pytest.mark.asyncio
async def test_gmail_architect():
    agent = GmailArchitect()
    result = await agent.process("check my mail")
    assert "GMAIL_ARCHITECT" in result["output"]

@pytest.mark.asyncio
async def test_manager_routing():
    manager = ManagerAgent()
    manager.register_agent(TradingSwarm())
    result = await manager.handle_request("Trade GC=F")
    assert "GC=F" in str(result)
