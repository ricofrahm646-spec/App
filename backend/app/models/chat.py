from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000)


class ChatAction(BaseModel):
    action: str
    target_module: str
    description: str


class ChatMessageResponse(BaseModel):
    summary: str
    actions: list[ChatAction]
