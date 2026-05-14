from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
import uvicorn
import logging

# J.A.R.V.I.S. V4000 Apex Core Imports
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.gmail_architect import GmailArchitect
from jarvis.agents.system_overlord import SystemOverlord
from jarvis.agents.neural_oracle import NeuralOracle
from jarvis.agents.neural_god import NeuralGod
from jarvis.core.nexus import NexusCore
from jarvis.core.meta_engine import MetaEngine
from jarvis.core.os_overlord import OSOverlord
from jarvis.core.mobile_shadow import MobileShadow
from jarvis.vision.kinetic import KineticVision
from jarvis.factory.autonomous_dev import AutonomousDev
from jarvis.ui.apex_interface import ApexHUD

from jarvis.factory.task_executor import TaskExecutor
from jarvis.core.evolution import EvolutionCore

# System Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_V4000_APEX")

app = FastAPI(title="JARVIS V4000 Apex Singularity API")

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
manager.register_agent(NeuralOracle())
manager.register_agent(NeuralGod())
manager.register_agent(NexusCore())
manager.register_agent(MetaEngine())
manager.register_agent(KineticVision())
manager.register_agent(OSOverlord())
manager.register_agent(MobileShadow())
manager.register_agent(AutonomousDev())

executor = TaskExecutor()
evolution = EvolutionCore()
apex_hud = ApexHUD()

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
        "status": "V4000_APEX_SINGULARITY_ONLINE",
        "timestamp": time.time(),
        "modules": ["NEURAL_GOD", "OS_OVERLORD", "MOBILE_SHADOW", "GHOST_PROGRAMMER", "APEX_HUD"]
    }

@app.post("/mission")
async def handle_mission_request(request: MissionRequest):
    """
    Central Mission Control Endpoint V4000 Apex.
    """
    mission_id = time.time()
    logger.info(f"MISSION_RECEIVED: {request.mission} (ID: {mission_id})")

    try:
        response = await manager.handle_request(request.mission)
        return response
    except Exception as e:
        logger.error(f"MISSION_FAILURE: {str(e)}")
        raise HTTPException(status_code=500, detail="MISSION_CONTROL_INTERRUPTED")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
