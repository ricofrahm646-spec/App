import asyncio
import logging
from typing import Dict, Any, List
from jarvis.agents.base import BaseAgent

class ManagerAgent:
    def __init__(self):
        self.agents = {}
        self.history = []
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MANAGER_AGENT")

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name.lower()] = agent
        self.logger.info(f"AGENT_REGISTERED: {agent.name}")

    async def handle_request(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        self.logger.info(f"DELEGATING_TASK: {task}")
        task_lower = task.lower()

        # V3000 Routing Logic
        if any(k in task_lower for k in ["predict", "gold", "market", "trade"]):
            target = "neuraloracle"
        elif any(k in task_lower for k in ["nexus", "memory", "auto", "pilot"]):
            target = "nexuscore"
        elif any(k in task_lower for k in ["gesture", "posture", "mode", "skeleton"]):
            target = "kineticvision"
        elif any(k in task_lower for k in ["refactor", "optimize", "kernel", "cpp"]):
            target = "metaengine"
        elif any(k in task_lower for k in ["mouse", "keyboard", "open", "type"]):
            target = "systemoverlord"
        elif any(k in task_lower for k in ["mail", "calendar", "inbox"]):
            target = "gmailarchitect"
        else:
            target = "tradingswarm" # Default legacy support

        if target in self.agents:
            return await self.agents[target].process(task, context)

        return {"output": f"ERROR: Target agent '{target}' not synchronized.", "agent": "manager"}
