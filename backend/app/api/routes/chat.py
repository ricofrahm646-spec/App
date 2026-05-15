from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.orchestrator import JarvisOrchestrator

router = APIRouter()
orchestrator = JarvisOrchestrator()


@router.post("/command", response_model=ChatResponse)
def process_command(request: ChatRequest) -> ChatResponse:
    return orchestrator.process_chat_command(request)
