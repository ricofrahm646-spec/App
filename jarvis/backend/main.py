from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
import uvicorn
import logging

# J.A.R.V.I.S. Core Imports
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.gmail_architect import GmailArchitect
from jarvis.agents.system_overlord import SystemOverlord
from jarvis.factory.task_executor import TaskExecutor
from jarvis.core.evolution import EvolutionCore
from jarvis.vision.spatial_core import SpatialVisionCore

# System Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_V1300_HUB")

app = FastAPI(title="JARVIS Singularity API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize All Core Systems
manager = ManagerAgent()
manager.register_agent(TradingSwarm())
manager.register_agent(GmailArchitect())
manager.register_agent(SystemOverlord())

executor = TaskExecutor()
evolution = EvolutionCore()
vision = SpatialVisionCore()

class MissionRequest(BaseModel):
    mission: str
    context: Optional[Dict[str, Any]] = None

@app.middleware("http")
async def mission_control_telemetry(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"MISSION_PATH: {request.url.path} - LATENCY: {process_time:.4f}s")
    return response

@app.get("/")
def health_check():
    return {
        "status": "SINGULARITY_ONLINE",
        "timestamp": time.time(),
        "modules": ["TRADING", "FACTORY", "COMM", "EVOLUTION", "VISION", "SYSTEM"]
    }

@app.post("/mission")
async def handle_mission_request(request: MissionRequest):
    """
    Central Mission Control Endpoint.
    Routes complex human intent to specialized autonomous agents.
    """
    mission_id = time.time()
    logger.info(f"MISSION_RECEIVED: {request.mission} (ID: {mission_id})")

    try:
        mission_lower = request.mission.lower()

        # Priority Agent Routing
        if any(k in mission_lower for k in ["trade", "gold", "forex", "pair", "market"]):
            response = await manager.handle_request(request.mission)
            return response

        if any(k in mission_lower for k in ["gmail", "calendar", "mail", "schedule"]):
            response = await manager.handle_request(request.mission)
            return response

        if any(k in mission_lower for k in ["mouse", "keyboard", "open", "type"]):
            response = await manager.handle_request(request.mission)
            return response

        # Autonomous Problem Solving via Factory
        result = await executor.execute_mission(request.mission)
        return {
            "response": f"FACTORY_MISSION_ACCOMPLISHED: {result['status']}",
            "agent": "factory",
            "data": result
        }

    except Exception as e:
        logger.error(f"MISSION_FAILURE: {str(e)}")
        raise HTTPException(status_code=500, detail="MISSION_CONTROL_INTERRUPTED")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
