import pytest
from jarvis.agents.trading import TradingAgent
from jarvis.agents.coding import CodingAgent
from jarvis.agents.system import SystemAgent
from jarvis.agents.manager import ManagerAgent

@pytest.mark.asyncio
async def test_trading_agent():
    agent = TradingAgent()
    result = await agent.process("What is the price of BTC?")
    assert "BTC-USD" in result["output"]
    assert "data" in result

@pytest.mark.asyncio
async def test_coding_agent():
    agent = CodingAgent()
    result = await agent.process("Design a new app")
    assert "UI design layout" in result["output"]

@pytest.mark.asyncio
async def test_system_agent():
    agent = SystemAgent()
    result = await agent.process("Open Chrome")
    assert "simulating opening chrome" in result["output"].lower()

@pytest.mark.asyncio
async def test_manager_routing():
    manager = ManagerAgent()
    manager.register_agent(TradingAgent())
    result = await manager.handle_request("Trade some crypto")
    assert result["agent"] == "trading"
