"""JARVIS FastAPI entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging_setup import logger, setup_logging
from backend.app.db.init_db import init_db
from backend.app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    logger.info("Starting {} ({})", settings.app_name, settings.app_env)
    await init_db()
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()
        logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        description="JARVIS — Full AI Trading Operating System",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "ok", "version": "0.1.0"}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "healthy"}

    return app


app = create_app()
