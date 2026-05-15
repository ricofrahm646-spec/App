import asyncio
from datetime import datetime

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


configure_logging(settings.log_level)

app = FastAPI(
    title="JARVIS Backend",
    version="0.1.0",
    description="AI Trading OS control plane and orchestration API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"service": "jarvis-backend", "status": "running"}


@app.websocket("/ws/status")
async def status_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "ai_status": "online",
                    "strategy_status": "adaptive",
                    "risk_lock": "inactive",
                }
            )
            await asyncio.sleep(2)
    except Exception:
        await websocket.close()
