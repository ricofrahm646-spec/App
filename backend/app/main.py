"""JARVIS FastAPI entrypoint."""

import asyncio
import contextlib
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_mt5
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.models import Base
from app.db.session import engine
from app.websocket.manager import manager, metrics_broadcast_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    def snapshot():
        mt5 = get_mt5()
        acc = mt5.account_info()
        return {"account": asdict(acc) if acc else None, "positions": mt5.positions()}

    task = asyncio.create_task(metrics_broadcast_loop(snapshot))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="JARVIS Trading OS",
    description="Modular AI-assisted trading control plane",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_root():
    return {"status": "ok", "service": "jarvis-backend"}


@app.websocket("/ws/v1/stream")
async def websocket_stream(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
