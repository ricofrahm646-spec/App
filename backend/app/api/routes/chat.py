"""AI chat endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.chat.engine import ChatEngine
from backend.app.db.models import ChatMessage
from backend.app.db.session import get_session
from backend.app.schemas.common import ChatTurn

router = APIRouter()
engine = ChatEngine()


class ChatRequest(BaseModel):
    message: str


@router.post("/send", response_model=ChatTurn)
async def send(req: ChatRequest, session: AsyncSession = Depends(get_session)) -> ChatTurn:
    user_msg = ChatMessage(role="user", content=req.message)
    session.add(user_msg)
    await session.commit()

    response = await engine.handle(req.message)

    bot_msg = ChatMessage(
        role="assistant",
        content=response.content,
        intent=response.intent,
        meta=response.meta,
    )
    session.add(bot_msg)
    await session.commit()
    return response


@router.get("/history", response_model=list[ChatTurn])
async def history(
    limit: int = 100, session: AsyncSession = Depends(get_session)
) -> list[ChatTurn]:
    rows = await session.scalars(
        select(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit)
    )
    items = list(rows)
    items.reverse()
    return [
        ChatTurn(role=m.role, content=m.content, intent=m.intent, meta=m.meta or {})
        for m in items
    ]
