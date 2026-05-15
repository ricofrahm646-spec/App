"""AI Chat routes.

Endpoints
---------
POST      /message – send a message and receive an AI response
GET       /history – retrieve chat history
WebSocket /ws      – real-time bidirectional chat
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.trade import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Payload for sending a chat message."""

    message: str = Field(..., min_length=1, max_length=4096)
    context: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    """AI response returned to the client."""

    id: int
    role: str
    content: str
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AI helper (placeholder – swap in your real LLM integration)
# ---------------------------------------------------------------------------


async def _generate_ai_response(
    message: str,
    history: list[ChatMessage],
    context: Optional[dict[str, Any]] = None,
) -> str:
    """Generate an AI response.

    Replace this stub with an actual call to OpenAI / local model once the
    AI subsystem is wired in.
    """
    if settings.OPENAI_API_KEY:
        try:
            import httpx

            messages = [{"role": "system", "content": (
                "You are JARVIS, an AI trading assistant. "
                "Help the user with trading analysis, strategy ideas, and market insights."
            )}]
            for msg in history[-20:]:
                messages.append({"role": msg.role, "content": msg.content})
            messages.append({"role": "user", "content": message})

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={"model": "gpt-4o", "messages": messages, "max_tokens": 1024},
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("OpenAI call failed, using fallback: %s", exc)

    return (
        f"I received your message: \"{message}\". "
        "AI integration is not fully configured yet. "
        "Please set OPENAI_API_KEY in your environment to enable full AI responses."
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/message", response_model=ChatResponse, status_code=201)
async def send_message(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatMessage:
    """Send a message to the AI and persist both sides of the conversation."""
    user_msg = ChatMessage(
        role="user",
        content=payload.message,
        metadata_json=payload.context,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user_msg)
    await db.flush()

    history_result = await db.execute(
        select(ChatMessage).order_by(ChatMessage.created_at.asc()).limit(50),
    )
    history = list(history_result.scalars().all())

    ai_text = await _generate_ai_response(payload.message, history, payload.context)

    assistant_msg = ChatMessage(
        role="assistant",
        content=ai_text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)
    return assistant_msg


@router.get("/history", response_model=list[ChatResponse])
async def chat_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    """Return paginated chat history, newest first."""
    result = await db.execute(
        select(ChatMessage)
        .order_by(ChatMessage.created_at.desc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all())


@router.websocket("/ws")
async def chat_websocket(ws: WebSocket) -> None:
    """Real-time bidirectional chat over WebSocket."""
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "Invalid JSON"})
                continue

            message = data.get("message", "")
            if not message:
                await ws.send_json({"error": "Empty message"})
                continue

            ai_text = await _generate_ai_response(message, [], data.get("context"))
            await ws.send_json({
                "role": "assistant",
                "content": ai_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except WebSocketDisconnect:
        logger.info("Chat WebSocket client disconnected")
