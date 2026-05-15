import pytest
import asyncio
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.quantum_liquidity import QuantumLiquidity
from jarvis.core.aether import AetherProtocol

@pytest.mark.asyncio
async def test_quantum_liquidity():
    agent = QuantumLiquidity()
    result = await agent.process("Check dark pools")
    assert "QUANTUM_LIQUIDITY_V5000" in result["output"]

@pytest.mark.asyncio
async def test_aether_evolution():
    agent = AetherProtocol()
    result = await agent.process("Engage Aether evolution")
    assert "AETHER_V5000" in result["output"]

@pytest.mark.asyncio
async def test_manager_routing_aether():
    manager = ManagerAgent()
    manager.register_agent(QuantumLiquidity())
    result = await manager.handle_request("Detect iceberg orders")
    assert "QUANTUM_LIQUIDITY" in str(result)
