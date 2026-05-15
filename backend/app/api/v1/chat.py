"""Chat endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chat_orchestrator import ChatOrchestrator

router = APIRouter()
_orchestrator = ChatOrchestrator()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


@router.post("/")
async def chat(req: ChatRequest):
    return await _orchestrator.handle_message(req.message)
