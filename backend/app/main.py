from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    ai_chat,
    backtesting,
    dashboard,
    mql5_routes,
    settings as settings_routes,
    strategies,
    telegram_routes,
    trading,
    tradingview_routes,
)
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.middleware.error_handler import ErrorHandlerMiddleware, register_error_handlers
from app.models.schemas import (
    APIResponse,
    HealthCheck,
    WSMessage,
    WSMessageType,
)

logger: structlog.stdlib.BoundLogger | None = None
_start_time: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# WebSocket connection manager
# ═══════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages active WebSocket connections for real-time broadcasting."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._subscriptions: dict[str, set[str]] = {}

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self._connections[client_id] = websocket
        self._subscriptions[client_id] = {"all"}
        _logger().info("ws_client_connected", client_id=client_id, total=self.active_count)

    def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        self._subscriptions.pop(client_id, None)
        _logger().info("ws_client_disconnected", client_id=client_id, total=self.active_count)

    def subscribe(self, client_id: str, channels: set[str]) -> None:
        if client_id in self._subscriptions:
            self._subscriptions[client_id].update(channels)

    def unsubscribe(self, client_id: str, channels: set[str]) -> None:
        if client_id in self._subscriptions:
            self._subscriptions[client_id] -= channels

    async def send_personal(self, client_id: str, message: WSMessage) -> None:
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message.model_dump(mode="json"))
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: WSMessage, channel: str = "all") -> None:
        disconnected: list[str] = []
        for cid, ws in self._connections.items():
            subs = self._subscriptions.get(cid, set())
            if channel in subs or "all" in subs:
                try:
                    await ws.send_json(message.model_dump(mode="json"))
                except Exception:
                    disconnected.append(cid)
        for cid in disconnected:
            self.disconnect(cid)

    async def broadcast_json(self, data: dict[str, Any], channel: str = "all") -> None:
        msg = WSMessage(
            type=WSMessageType.ACCOUNT_UPDATE,
            data=data,
        )
        await self.broadcast(msg, channel)


manager = ConnectionManager()


def _logger() -> structlog.stdlib.BoundLogger:
    global logger
    if logger is None:
        logger = structlog.get_logger("jarvis.main")
    return logger


# ═══════════════════════════════════════════════════════════════════════════
# Heartbeat background task
# ═══════════════════════════════════════════════════════════════════════════

async def _heartbeat_loop() -> None:
    """Send periodic heartbeats to all connected WebSocket clients."""
    while True:
        await asyncio.sleep(15)
        if manager.active_count > 0:
            await manager.broadcast(
                WSMessage(
                    type=WSMessageType.HEARTBEAT,
                    data={"server_time": datetime.now(timezone.utc).isoformat()},
                )
            )


# ═══════════════════════════════════════════════════════════════════════════
# Lifespan
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _start_time
    setup_logging()
    _start_time = time.monotonic()

    log = _logger()
    settings = get_settings()
    log.info(
        "jarvis_starting",
        version=settings.app_version,
        environment=settings.environment.value,
    )

    heartbeat_task = asyncio.create_task(_heartbeat_loop())

    yield

    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

    log.info("jarvis_shutdown")


# ═══════════════════════════════════════════════════════════════════════════
# Application factory
# ═══════════════════════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "JARVIS — AI-powered Trading Operating System. "
            "Manage strategies, execute trades, run backtests, generate MQL5 code, "
            "and interact with an AI trading assistant."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Error handling middleware ─────────────────────────────────────────
    app.add_middleware(ErrorHandlerMiddleware)
    register_error_handlers(app)

    # ── API routers ──────────────────────────────────────────────────────
    prefix = settings.api_prefix
    app.include_router(trading.router, prefix=prefix)
    app.include_router(strategies.router, prefix=prefix)
    app.include_router(backtesting.router, prefix=prefix)
    app.include_router(ai_chat.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(telegram_routes.router, prefix=prefix)
    app.include_router(tradingview_routes.router, prefix=prefix)
    app.include_router(mql5_routes.router, prefix=prefix)
    app.include_router(settings_routes.router, prefix=prefix)

    # ── Health check ─────────────────────────────────────────────────────

    @app.get(
        "/health",
        response_model=HealthCheck,
        tags=["Health"],
        summary="Health check",
    )
    async def health_check() -> HealthCheck:
        uptime = time.monotonic() - _start_time if _start_time else 0.0
        return HealthCheck(
            status="ok",
            version=settings.app_version,
            environment=settings.environment.value,
            uptime_seconds=round(uptime, 2),
            services={
                "api": True,
                "websocket": True,
                "mt5_bridge": False,
                "redis": False,
                "database": False,
            },
        )

    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "name": settings.app_name,
                "version": settings.app_version,
                "status": "running",
                "docs": "/docs",
            }
        )

    # ── Dashboard WebSocket ──────────────────────────────────────────────

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
        await manager.connect(websocket, client_id)
        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "subscribe":
                    channels = set(data.get("channels", []))
                    manager.subscribe(client_id, channels)
                    await manager.send_personal(
                        client_id,
                        WSMessage(
                            type=WSMessageType.ACCOUNT_UPDATE,
                            data={"subscribed": list(channels)},
                        ),
                    )

                elif action == "unsubscribe":
                    channels = set(data.get("channels", []))
                    manager.unsubscribe(client_id, channels)

                elif action == "ping":
                    await manager.send_personal(
                        client_id,
                        WSMessage(
                            type=WSMessageType.HEARTBEAT,
                            data={"pong": True},
                        ),
                    )

        except WebSocketDisconnect:
            manager.disconnect(client_id)
        except Exception as exc:
            _logger().error("ws_error", client_id=client_id, error=str(exc))
            manager.disconnect(client_id)

    return app


app = create_app()
