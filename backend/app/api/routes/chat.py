from fastapi import APIRouter

from app.dependencies import chat_orchestrator
from app.models.chat import ChatMessageRequest, ChatMessageResponse

router = APIRouter()


@router.post("/message", response_model=ChatMessageResponse)
def send_message(payload: ChatMessageRequest) -> ChatMessageResponse:
    return chat_orchestrator.process_message(payload.message)
