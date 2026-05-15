"""MT5 REST surface."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_mt5
from app.core.config import settings
from app.services.mt5_installer import MT5Installer

router = APIRouter()


class InstallMq5Request(BaseModel):
    relative_path: str = Field(
        description="Path under JARVIS workspace, e.g. mql5/generated/JarvisEA_XAUUSD.mq5",
    )
    kind: Literal["expert", "indicator"]


@router.get("/account")
async def account():
    mt5 = get_mt5()
    snap = mt5.account_info()
    if snap is None:
        return {"connected": False}
    return {
        "connected": True,
        "balance": snap.balance,
        "equity": snap.equity,
        "margin": snap.margin,
        "margin_free": snap.margin_free,
        "server": snap.server,
        "currency": snap.currency,
    }


@router.get("/positions")
async def positions():
    mt5 = get_mt5()
    return {"positions": mt5.positions()}


@router.post("/install-mq5")
async def install_mq5(body: InstallMq5Request):
    root = Path(settings.jarvis_workspace_root).resolve()
    source = (root / body.relative_path).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc
    if not source.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    installer = MT5Installer()
    try:
        dest = installer.install_mq5(source, body.kind)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"installed_to": str(dest)}
