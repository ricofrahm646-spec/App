from typing import Dict, Any, List
from jarvis.agents.base import BaseAgent

class ManagerAgent:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name.lower()] = agent

    async def handle_request(self, message: str) -> Dict[str, Any]:
        # Simple routing logic
        if "trade" in message.lower() or "chart" in message.lower():
            target = "trading"
        elif "code" in message.lower() or "app" in message.lower() or "design" in message.lower():
            target = "coding"
        elif "open" in message.lower() or "system" in message.lower() or "mouse" in message.lower():
            target = "system"
        else:
            return {"response": f"I am JARVIS. How can I help you? (Detected: {message})", "agent": "manager"}

        if target in self.agents:
            result = await self.agents[target].process(message)
            return {"response": result.get("output", "Error processing request"), "agent": target, "data": result.get("data")}

        return {"response": f"The {target} agent is not yet registered.", "agent": "manager"}
