"""JARVIS Trading OS – FastAPI application entry point."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Configuration ─────────────────────────────────────────────────────────────
# Primary async config (PostgreSQL system)
try:
    from app.config import settings as async_settings
    _ASYNC_SETTINGS_AVAILABLE = True
except Exception:
    async_settings = None  # type: ignore
    _ASYNC_SETTINGS_AVAILABLE = False

# JARVIS sync config (SQLite system)
from app.core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Initialise JARVIS sync SQLite database
    from app.database import init_db
    init_db()
    logger.info("JARVIS SQLite database initialised")

    # Optionally initialise async PostgreSQL database
    if _ASYNC_SETTINGS_AVAILABLE:
        try:
            from app.core.database import init_db as async_init_db
            await async_init_db()
            logger.info("Async PostgreSQL database initialised")
        except Exception as exc:
            logger.warning("Async database init skipped (non-critical): %s", exc)

    # Auto-connect MT5
    if settings.MT5_LOGIN and settings.MT5_PASSWORD:
        from app.services.mt5_service import MT5Service
        result = MT5Service.connect(
            login=settings.MT5_LOGIN,
            password=settings.MT5_PASSWORD,
            server=settings.MT5_SERVER,
            path=settings.MT5_PATH,
        )
        logger.info("MT5 auto-connect: %s", result.get("message"))

    logger.info("JARVIS backend ready.")
    yield

    # Graceful shutdown
    logger.info("Shutting down JARVIS backend…")
    from app.services.mt5_service import MT5Service
    MT5Service.disconnect()

    if _ASYNC_SETTINGS_AVAILABLE:
        try:
            from app.core.database import close_db
            await close_db()
        except Exception:
            pass

    logger.info("Shutdown complete.")


# ── Application factory ────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "JARVIS AI Trading OS – Production-ready REST + WebSocket API for "
        "MetaTrader 5 automation, AI-powered strategy generation, backtesting, "
        "real-time risk management, and multi-channel notifications."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Any:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed}ms"
    return response


# ── Exception handlers ─────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body) if hasattr(exc, "body") else None},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ── JARVIS Trading OS Routers ─────────────────────────────────────────────────

from app.api.routes.trading import router as trading_router
from app.api.routes.ai import router as ai_router
from app.api.routes.strategies import router as strategies_router
from app.api.routes.backtesting import router as backtesting_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.telegram import router as telegram_router
from app.api.routes.tradingview import router as tradingview_router
from app.api.routes.mql5 import router as mql5_router
from app.api.routes.risk import router as risk_router

app.include_router(trading_router)
app.include_router(ai_router)
app.include_router(strategies_router)
app.include_router(backtesting_router)
app.include_router(dashboard_router)
app.include_router(telegram_router)
app.include_router(tradingview_router)
app.include_router(mql5_router)
app.include_router(risk_router)

# ── Legacy async routes (auth, trades, market) ────────────────────────────────

if _ASYNC_SETTINGS_AVAILABLE:
    try:
        from app.api.routes.auth import router as auth_router
        from app.api.routes.trades import router as trades_router
        from app.api.routes.market import router as market_router
        from app.api.routes.settings import router as settings_router_legacy
        from app.api.routes.webhook import router as webhook_router
        app.include_router(auth_router)
        app.include_router(trades_router)
        app.include_router(market_router)
        app.include_router(settings_router_legacy)
        app.include_router(webhook_router)
        logger.info("Legacy async routes registered (auth, trades, market, settings, webhook)")
    except Exception as exc:
        logger.warning("Legacy async routes unavailable (non-critical): %s", exc)


# ── Health / system endpoints ──────────────────────────────────────────────────

@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health() -> dict:
    from app.services.mt5_service import MT5Service
    return {
        "status": "healthy",
        "mt5_connected": MT5Service.is_connected(),
        "version": settings.APP_VERSION,
    }


@app.get("/api/status", tags=["system"])
def api_status() -> dict:
    from app.services.mt5_service import MT5Service
    mt5 = MT5Service.get_status()
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mt5": mt5,
        "ai_providers": {
            "openai": bool(settings.OPENAI_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
        },
    }
