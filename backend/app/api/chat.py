from fastapi import APIRouter, Depends

from ai.chat_orchestrator import ChatOrchestrator
from backend.app.dependencies import get_chat_orchestrator
from backend.app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
) -> ChatResponse:
    return orchestrator.handle(request.message, dry_run=request.dry_run)
