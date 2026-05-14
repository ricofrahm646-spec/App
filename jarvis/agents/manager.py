from typing import Dict, Any, List
from jarvis.agents.base import BaseAgent

class ManagerAgent:
    """
    """
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name.lower()] = agent

    async def handle_request(self, message: str) -> Dict[str, Any]:
        msg = message.lower()
        if "trade" in msg or "chart" in msg or "gold" in msg or "forex" in msg:
            target = "tradingswarm"
        elif "mail" in msg or "gmail" in msg or "calendar" in msg:
            target = "commcommander"
        elif "code" in msg or "app" in msg:
            target = "coding"
        elif "system" in msg or "open" in msg:
            target = "system"
        else:
            return {"response": "J.A.R.V.I.S. READY. AWAITING MISSION.", "agent": "manager"}

        if target in self.agents:
            return await self.agents[target].process(message)
        return {"response": f"NODE_{target.upper()} UNREACHABLE", "agent": "manager"}
