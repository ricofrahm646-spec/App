"""MQL5 generator + auto-installer endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mql5.generator import MQL5Generator
from mql5.installer import MQL5Installer

router = APIRouter()


class EARequest(BaseModel):
    name: str
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    strategy_kind: str = "trend_following"
    parameters: dict[str, Any] = {}


@router.post("/generate-ea")
async def generate_ea(req: EARequest) -> dict[str, Any]:
    gen = MQL5Generator()
    file_path = gen.generate_ea(
        name=req.name,
        symbol=req.symbol,
        timeframe=req.timeframe,
        strategy_kind=req.strategy_kind,
        parameters=req.parameters,
    )
    return {"path": str(file_path)}


class IndicatorRequest(BaseModel):
    name: str
    kind: str = "rsi_divergence"
    parameters: dict[str, Any] = {}


@router.post("/generate-indicator")
async def generate_indicator(req: IndicatorRequest) -> dict[str, Any]:
    gen = MQL5Generator()
    file_path = gen.generate_indicator(name=req.name, kind=req.kind, parameters=req.parameters)
    return {"path": str(file_path)}


class InstallRequest(BaseModel):
    file_path: str
    kind: str = "ea"  # ea | indicator


@router.post("/install")
async def install(req: InstallRequest) -> dict[str, str]:
    installer = MQL5Installer()
    try:
        target = installer.install(req.file_path, kind=req.kind)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"installed_to": str(target)}


@router.get("/list")
async def list_generated() -> list[dict[str, Any]]:
    gen = MQL5Generator()
    return gen.list_generated()
