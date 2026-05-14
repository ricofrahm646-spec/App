import pytest
import asyncio
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.gmail_architect import GmailArchitect
from jarvis.agents.neural_oracle import NeuralOracle

@pytest.mark.asyncio
async def test_trading_swarm():
    agent = TradingSwarm()
    result = await agent.process("trade gold")
    # In V3000, trade requests are now intercepted by Manager for NeuralOracle
    assert "TRADING_SWARM" in result["output"] or "QUANTUM" in result["output"]

@pytest.mark.asyncio
async def test_gmail_architect():
    agent = GmailArchitect()
    result = await agent.process("check my mail")
    assert "GMAIL_ARCHITECT" in result["output"]

@pytest.mark.asyncio
async def test_manager_routing():
    manager = ManagerAgent()
    manager.register_agent(TradingSwarm())
    manager.register_agent(NeuralOracle())
    result = await manager.handle_request("Trade GC=F")
    assert "NEURAL_ORACLE" in str(result)
