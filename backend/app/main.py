from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas import ChatCommandRequest, ChatCommandResponse, SystemOverview
from app.services.orchestrator import JarvisOrchestrator

settings = get_settings()
orchestrator = JarvisOrchestrator(settings=settings)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="JARVIS orchestration backend for AI-assisted trading operations",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "jarvis-backend"}


@app.get("/api/v1/system/overview", response_model=SystemOverview)
async def system_overview() -> SystemOverview:
    return orchestrator.system_overview()


@app.post("/api/v1/chat/command", response_model=ChatCommandResponse)
async def chat_command(payload: ChatCommandRequest) -> ChatCommandResponse:
    try:
        return orchestrator.process_command(payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
