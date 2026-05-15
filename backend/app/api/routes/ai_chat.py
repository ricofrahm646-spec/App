from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from app.models.schemas import (
    APIResponse,
    ChatHistoryResponse,
    ChatMessage,
    ChatMessageRequest,
    ChatRole,
    WSMessage,
    WSMessageType,
)

logger = structlog.get_logger("jarvis.ai_chat")
router = APIRouter(prefix="/ai", tags=["AI Chat"])

_chat_history: list[ChatMessage] = []
_MAX_HISTORY = 500

JARVIS_RESPONSES: list[str] = [
    "Based on my analysis, the current market structure for {symbol} shows a "
    "potential {direction} setup. The key levels to watch are the support at "
    "{s_level} and resistance at {r_level}. I'd recommend waiting for a "
    "confirmation candle before entering.",
    "Looking at the recent price action, I notice a divergence forming on the "
    "RSI which could signal a reversal. Consider tightening your stop loss on "
    "existing positions.",
    "The risk-reward ratio for this trade setup is approximately 1:{rr}. "
    "Given your current account balance and risk parameters, I'd suggest a "
    "position size of {lots} lots.",
    "I've analyzed the correlation between your open positions. Currently, "
    "you have a high positive correlation exposure which increases portfolio "
    "risk. Consider diversifying across uncorrelated pairs.",
    "The economic calendar shows several high-impact events this week. I'd "
    "recommend reducing position sizes ahead of the NFP release on Friday.",
]


def _generate_response(user_message: str) -> str:
    """Generate a contextual response based on user input."""
    msg_lower = user_message.lower()
    rng_seed = hash(user_message) % len(JARVIS_RESPONSES)

    if any(w in msg_lower for w in ("analyze", "analysis", "chart", "look at")):
        return JARVIS_RESPONSES[0].format(
            symbol="EURUSD", direction="bullish", s_level="1.0850", r_level="1.0950"
        )
    if any(w in msg_lower for w in ("risk", "position size", "lot")):
        return JARVIS_RESPONSES[2].format(rr="2.5", lots="0.15")
    if any(w in msg_lower for w in ("portfolio", "correlation", "exposure")):
        return JARVIS_RESPONSES[3]
    if any(w in msg_lower for w in ("news", "calendar", "event", "nfp")):
        return JARVIS_RESPONSES[4]
    if any(w in msg_lower for w in ("rsi", "divergence", "indicator")):
        return JARVIS_RESPONSES[1]

    return (
        f"I've processed your request: \"{user_message[:80]}...\" "
        "Here's my analysis: The current market conditions suggest maintaining "
        "a cautious approach. I recommend reviewing your strategy parameters "
        "and ensuring your risk management rules are properly configured. "
        "Would you like me to run a detailed analysis on a specific pair?"
    )


async def _generate_response_chunks(user_message: str):
    """Yield response word-by-word for streaming."""
    full = _generate_response(user_message)
    words = full.split()
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        await asyncio.sleep(0.03)


# ── Send message ─────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=APIResponse,
    summary="Send a chat message and get AI response",
)
async def send_message(request: ChatMessageRequest) -> APIResponse:
    user_msg = ChatMessage(
        id=uuid.uuid4().hex[:12],
        role=ChatRole.USER,
        content=request.message,
        timestamp=datetime.now(timezone.utc),
        metadata=request.context,
    )
    _chat_history.append(user_msg)

    response_text = _generate_response(request.message)

    assistant_msg = ChatMessage(
        id=uuid.uuid4().hex[:12],
        role=ChatRole.ASSISTANT,
        content=response_text,
        timestamp=datetime.now(timezone.utc),
    )
    _chat_history.append(assistant_msg)

    if len(_chat_history) > _MAX_HISTORY:
        _chat_history[:] = _chat_history[-_MAX_HISTORY:]

    logger.info(
        "chat_message",
        user_msg_len=len(request.message),
        response_len=len(response_text),
    )
    return APIResponse(
        success=True,
        data=assistant_msg.model_dump(mode="json"),
    )


# ── Get chat history ────────────────────────────────────────────────────

@router.get(
    "/chat/history",
    response_model=APIResponse,
    summary="Retrieve chat history",
)
async def get_chat_history(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> APIResponse:
    total = len(_chat_history)
    messages = _chat_history[offset : offset + limit]
    return APIResponse(
        success=True,
        data=ChatHistoryResponse(
            messages=messages,
            total=total,
        ).model_dump(mode="json"),
    )


# ── Clear chat history ──────────────────────────────────────────────────

@router.delete(
    "/chat/history",
    response_model=APIResponse,
    summary="Clear chat history",
)
async def clear_chat_history() -> APIResponse:
    count = len(_chat_history)
    _chat_history.clear()
    logger.info("chat_history_cleared", count=count)
    return APIResponse(success=True, message=f"Cleared {count} messages.")


# ── WebSocket streaming ─────────────────────────────────────────────────

@router.websocket("/chat/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("ai_chat_ws_connected")

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            if not message:
                await websocket.send_json(
                    WSMessage(
                        type=WSMessageType.ERROR,
                        data={"error": "Empty message"},
                    ).model_dump(mode="json")
                )
                continue

            user_msg = ChatMessage(
                id=uuid.uuid4().hex[:12],
                role=ChatRole.USER,
                content=message,
                timestamp=datetime.now(timezone.utc),
            )
            _chat_history.append(user_msg)

            full_response = ""
            async for chunk in _generate_response_chunks(message):
                full_response += chunk
                await websocket.send_json(
                    WSMessage(
                        type=WSMessageType.AI_CHAT_CHUNK,
                        data={"chunk": chunk},
                    ).model_dump(mode="json")
                )

            assistant_msg = ChatMessage(
                id=uuid.uuid4().hex[:12],
                role=ChatRole.ASSISTANT,
                content=full_response,
                timestamp=datetime.now(timezone.utc),
            )
            _chat_history.append(assistant_msg)

            await websocket.send_json(
                WSMessage(
                    type=WSMessageType.AI_CHAT_DONE,
                    data=assistant_msg.model_dump(mode="json"),
                ).model_dump(mode="json")
            )

    except WebSocketDisconnect:
        logger.info("ai_chat_ws_disconnected")
    except Exception as exc:
        logger.error("ai_chat_ws_error", error=str(exc))
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
