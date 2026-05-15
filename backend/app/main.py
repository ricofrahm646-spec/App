"""JARVIS Trading OS – FastAPI application entry point."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.database import close_db, init_db
from app.core.logging import logger
from app.core.websocket import ws_manager

# ── Routers ────────────────────────────────────────────────────────────────────
from app.api.routes.auth import router as auth_router
from app.api.routes.trades import router as trades_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.market import router as market_router
from app.api.routes.settings import router as settings_router
from app.api.routes.webhook import router as webhook_router


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown logic."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: DEBUG={settings.DEBUG}  LOG_LEVEL={settings.LOG_LEVEL}")

    # Initialise database tables
    try:
        await init_db()
    except Exception as exc:
        logger.error(f"Database initialisation failed: {exc}")
        raise

    logger.info("JARVIS backend is ready to accept connections.")
    yield

    # Graceful shutdown
    logger.info("Shutting down JARVIS backend…")
    await close_db()
    logger.info("Shutdown complete.")


# ── Application factory ────────────────────────────────────────────────────────

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "JARVIS – Professional AI Trading OS backend API. "
            "Provides REST endpoints for trade management, strategy control, "
            "market data, AI analysis, and real-time WebSocket feeds."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_and_timing(
        request: Request, call_next: Any
    ) -> Any:
        """Attach a unique request ID and log request duration."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        logger.debug(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={elapsed_ms:.2f}ms "
            f"request_id={request_id}"
        )
        return response

    # ── Exception handlers ─────────────────────────────────────────────────────

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # ── Routers ────────────────────────────────────────────────────────────────

    API_PREFIX = "/api/v1"

    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(trades_router, prefix=API_PREFIX)
    app.include_router(strategies_router, prefix=API_PREFIX)
    app.include_router(market_router, prefix=API_PREFIX)
    app.include_router(settings_router, prefix=API_PREFIX)
    app.include_router(webhook_router, prefix=API_PREFIX)

    # ── WebSocket endpoint ─────────────────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Primary WebSocket endpoint for real-time market and trade events.

        Clients may optionally pass `?token=<jwt>` as a query parameter to
        bind the connection to an authenticated user.
        """
        client_id = str(uuid.uuid4())
        user_id: int | None = None

        # Optional JWT authentication via query param
        token = websocket.query_params.get("token")
        if token:
            try:
                from app.core.security import decode_access_token
                token_data = decode_access_token(token)
                user_id = token_data.user_id
            except Exception:
                # Connection is still accepted but unauthenticated
                logger.warning(f"WebSocket {client_id}: invalid token provided")

        await ws_manager.connect(websocket, client_id, user_id=user_id)
        logger.info(
            f"WebSocket client connected: id={client_id} user_id={user_id} "
            f"total_connections={ws_manager.active_connections}"
        )

        try:
            while True:
                raw_message = await websocket.receive_text()
                await ws_manager.handle_client_message(client_id, raw_message)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.error(f"WebSocket {client_id} error: {exc}")
        finally:
            await ws_manager.disconnect(client_id)
            logger.info(
                f"WebSocket client disconnected: id={client_id} "
                f"total_connections={ws_manager.active_connections}"
            )

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint_with_id(
        websocket: WebSocket, client_id: str
    ) -> None:
        """WebSocket endpoint that accepts a client-provided ID."""
        user_id: int | None = None
        token = websocket.query_params.get("token")
        if token:
            try:
                from app.core.security import decode_access_token
                token_data = decode_access_token(token)
                user_id = token_data.user_id
            except Exception:
                logger.warning(f"WebSocket {client_id}: invalid token")

        await ws_manager.connect(websocket, client_id, user_id=user_id)
        try:
            while True:
                raw_message = await websocket.receive_text()
                await ws_manager.handle_client_message(client_id, raw_message)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.error(f"WebSocket {client_id} error: {exc}")
        finally:
            await ws_manager.disconnect(client_id)

    # ── Static files ───────────────────────────────────────────────────────────

    import os

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # ── Health & status endpoints ──────────────────────────────────────────────

    @app.get("/health", tags=["System"], summary="Basic liveness probe")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}

    @app.get("/api/v1/status", tags=["System"], summary="Detailed system status")
    async def system_status() -> dict[str, Any]:
        from app.core.database import engine

        db_ok = False
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:
            logger.error(f"DB health check failed: {exc}")

        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "ok" if db_ok else "degraded",
            "components": {
                "database": "ok" if db_ok else "error",
                "websocket": {
                    "active_connections": ws_manager.active_connections,
                },
            },
            "debug": settings.DEBUG,
        }

    @app.get("/api/v1/ws/connections", tags=["System"], summary="Active WebSocket connections")
    async def ws_connections() -> dict[str, Any]:
        return {
            "active_connections": ws_manager.active_connections,
            "connections": ws_manager.get_connection_list(),
        }

    return app


# ── ASGI entrypoint ────────────────────────────────────────────────────────────

app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1,
    )
