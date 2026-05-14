from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.comm_commander import CommCommander
from jarvis.factory.task_executor import TaskExecutor
import uvicorn

app = FastAPI(title="JARVIS V1000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize V1000 Core
manager = ManagerAgent()
manager.register_agent(TradingSwarm())
manager.register_agent(CommCommander())

executor = TaskExecutor()

class MissionRequest(BaseModel):
    mission: str
    context: Optional[Dict[str, Any]] = None

@app.get("/")
def health():
    return {"status": "JARVIS_V1000_ONLINE"}

@app.post("/mission")
async def handle_mission(request: MissionRequest):
    try:
        # Check if it's a known agent task or a general mission
        mission_lower = request.mission.lower()

        if any(keyword in mission_lower for keyword in ["trade", "gold", "forex", "mail", "gmail", "calendar"]):
            response = await manager.handle_request(request.mission)
            return response

        # Default to Task Executor for complex missions
        result = await executor.execute_mission(request.mission)
        return {
            "response": f"Mission Received: {result['mission']}. {result['status']}. All sub-tasks processed in Sandbox.",
            "agent": "factory",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
