"""JARVIS AI Trading Operating System – FastAPI application entry point."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import account, chat, mt5, settings_routes, strategies, trades
from app.core.config import settings
from app.core.database import close_db, init_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection managers (Redis, MT5) stored as app state
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections for live data streaming."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""

    # -- startup --
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    await init_db()
    logger.info("Database initialised")

    # Redis (best-effort; the app can still serve most endpoints without it)
    try:
        import redis.asyncio as aioredis

        app.state.redis = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True,
        )
        await app.state.redis.ping()
        logger.info("Redis connected at %s", settings.REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable – continuing without cache: %s", exc)
        app.state.redis = None

    # MT5 flag
    app.state.mt5_connected = False

    yield

    # -- shutdown --
    if getattr(app.state, "redis", None) is not None:
        await app.state.redis.close()
        logger.info("Redis connection closed")

    await close_db()
    logger.info("Database connection pool closed")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["Strategies"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(account.router, prefix="/api/account", tags=["Account"])
app.include_router(mt5.router, prefix="/api/mt5", tags=["MT5"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Return basic service health information."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# WebSocket – live data feed
# ---------------------------------------------------------------------------


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket) -> None:
    """Stream live account, trade, and signal data to connected clients."""
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"error": "invalid JSON"})
                continue

            msg_type = msg.get("type", "ping")
            if msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})
            elif msg_type == "subscribe":
                await ws.send_json({"type": "subscribed", "channel": msg.get("channel")})
            else:
                await ws.send_json({"type": "ack", "received": msg_type})
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
