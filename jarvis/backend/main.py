from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
import uvicorn
import logging

# J.A.R.V.I.S. V9000 Aethelgard Omega Core Imports
from jarvis.core.omega.kernel_v9000 import NeuralOverlordKernel
from jarvis.core.omega.global_nexus import GlobalNexus
from jarvis.core.omega.immortality import ImmortalityProtocol
from jarvis.agents.trading.temporal.oracle_v9 import TemporalTradingKernelV9
from jarvis.core.hive_mind import HiveMind
from jarvis.agents.manager import ManagerAgent
from jarvis.agents.trading_swarm import TradingSwarm
from jarvis.agents.gmail_architect import GmailArchitect
from jarvis.agents.system_overlord import SystemOverlord
from jarvis.agents.neural_oracle import NeuralOracle
from jarvis.agents.neural_god import NeuralGod
from jarvis.agents.quantum_liquidity import QuantumLiquidity
from jarvis.core.nexus import NexusCore
from jarvis.core.meta_engine import MetaEngine
from jarvis.core.os_overlord import OSOverlord
from jarvis.core.mobile_shadow import MobileShadow
from jarvis.core.os_fusion import OSFusion
from jarvis.core.aether import AetherProtocol
from jarvis.vision.kinetic import KineticVision
from jarvis.vision.bio_sense import BioSense
from jarvis.factory.autonomous_dev import AutonomousDev
from jarvis.factory.passive_income_swarm import PassiveIncomeSwarm
from jarvis.ui.apex_interface import ApexHUD

from jarvis.factory.task_executor import TaskExecutor
from jarvis.core.evolution import EvolutionCore

# System Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS_V5000_AETHER")

app = FastAPI(title="JARVIS V9000 Aethelgard Omega API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize All Core Systems
kernel = NeuralOverlordKernel()
nexus = GlobalNexus()
immortality = ImmortalityProtocol()
temporal_trading = TemporalTradingKernelV9()

hive = HiveMind()
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
manager.register_agent(QuantumLiquidity())
manager.register_agent(BioSense())
manager.register_agent(PassiveIncomeSwarm())
manager.register_agent(OSFusion())
manager.register_agent(AetherProtocol())

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
        "status": "V9000_AETHELGARD_OMEGA_ONLINE",
        "timestamp": time.time(),
        "active_agents": len(manager.agents),
        "swarm_nodes": hive.get_telemetry()["active_nodes"],
        "throughput": kernel.calculate_temporal_throughput(),
        "immortality": immortality.get_immortality_status(),
        "sovereignty_level": "AETHELGARD_SINGULARITY"
    }

@app.post("/mission")
async def handle_mission_request(request: MissionRequest):
    """
    Central Mission Control Endpoint V6000 Nebula Hive.
    """
    mission_id = time.time()
    logger.info(f"MISSION_RECEIVED: {request.mission} (ID: {mission_id})")

    try:
        # Route through Hive Mind for swarm orchestration
        hive_response = await hive.process_missions(request.mission)
        manager_response = await manager.handle_request(request.mission)

        return {
            "manager_output": manager_response,
            "hive_status": hive_response,
            "telemetry": hive.get_telemetry()
        }
    except Exception as e:
        logger.error(f"MISSION_FAILURE: {str(e)}")
        raise HTTPException(status_code=500, detail="NEBULA_HIVE_INTERRUPTED")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
