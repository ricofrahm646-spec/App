import pytest
import asyncio
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.gmail_architect import GmailArchitect
from jarvis.agents.neural_oracle import NeuralOracle
from jarvis.agents.neural_god import NeuralGod

@pytest.mark.asyncio
async def test_trading_swarm():
    agent = TradingSwarm()
    result = await agent.process("trade gold")
    assert "TRADING_SWARM" in result["output"] or "QUANTUM" in result["output"]

@pytest.mark.asyncio
async def test_neural_god():
    agent = NeuralGod()
    result = await agent.process("feel the heartbeat")
    assert "NEURAL_GOD_V4000" in result["output"]

@pytest.mark.asyncio
async def test_manager_routing_apex():
    manager = ManagerAgent()
    manager.register_agent(NeuralGod())
    result = await manager.handle_request("Optimize intuition")
    assert "NEURAL_GOD" in str(result)
