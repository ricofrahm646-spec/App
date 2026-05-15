"""MetaTrader 5 integration routes.

Endpoints
---------
POST /connect – connect to MT5 terminal
GET  /status  – check connection status
GET  /symbols – list available trading symbols
GET  /charts  – info about open charts
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MT5ConnectRequest(BaseModel):
    """Credentials for connecting to the MT5 terminal."""

    path: Optional[str] = None
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None


class MT5StatusResponse(BaseModel):
    """Current MT5 connection status."""

    connected: bool
    login: int = 0
    server: str = ""
    balance: float = 0.0
    equity: float = 0.0
    leverage: int = 0
    company: str = ""


class SymbolInfo(BaseModel):
    """Minimal symbol information."""

    name: str
    description: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: int = 0
    digits: int = 0
    trade_mode: str = ""


# ---------------------------------------------------------------------------
# MT5 helper layer
# ---------------------------------------------------------------------------


def _get_mt5():
    """Lazily import MetaTrader5 – it's only available on Windows."""
    try:
        import MetaTrader5 as mt5
        return mt5
    except ImportError:
        return None


async def _ensure_connected(request: Request) -> None:
    if not getattr(request.app.state, "mt5_connected", False):
        raise HTTPException(status_code=503, detail="MT5 is not connected")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/connect", response_model=MT5StatusResponse)
async def connect_mt5(payload: MT5ConnectRequest, request: Request) -> MT5StatusResponse:
    """Initialise and authenticate with the MT5 terminal."""
    mt5 = _get_mt5()
    if mt5 is None:
        logger.warning("MetaTrader5 package not available on this platform")
        request.app.state.mt5_connected = False
        raise HTTPException(
            status_code=501,
            detail="MetaTrader5 is not available on this platform",
        )

    path = payload.path or settings.MT5_PATH
    login = payload.login or settings.MT5_LOGIN
    password = payload.password or settings.MT5_PASSWORD
    server = payload.server or settings.MT5_SERVER

    init_kwargs: dict[str, Any] = {}
    if path:
        init_kwargs["path"] = path

    if not mt5.initialize(**init_kwargs):
        request.app.state.mt5_connected = False
        raise HTTPException(
            status_code=502,
            detail=f"MT5 initialization failed: {mt5.last_error()}",
        )

    if login:
        authorised = mt5.login(login=login, password=password, server=server)
        if not authorised:
            mt5.shutdown()
            request.app.state.mt5_connected = False
            raise HTTPException(
                status_code=401,
                detail=f"MT5 login failed: {mt5.last_error()}",
            )

    request.app.state.mt5_connected = True
    info = mt5.account_info()

    return MT5StatusResponse(
        connected=True,
        login=info.login if info else 0,
        server=info.server if info else "",
        balance=info.balance if info else 0.0,
        equity=info.equity if info else 0.0,
        leverage=info.leverage if info else 0,
        company=info.company if info else "",
    )


@router.get("/status", response_model=MT5StatusResponse)
async def mt5_status(request: Request) -> MT5StatusResponse:
    """Return the current MT5 connection status."""
    mt5 = _get_mt5()
    connected = getattr(request.app.state, "mt5_connected", False)

    if not connected or mt5 is None:
        return MT5StatusResponse(connected=False)

    info = mt5.account_info()
    if info is None:
        request.app.state.mt5_connected = False
        return MT5StatusResponse(connected=False)

    return MT5StatusResponse(
        connected=True,
        login=info.login,
        server=info.server,
        balance=info.balance,
        equity=info.equity,
        leverage=info.leverage,
        company=info.company,
    )


@router.get("/symbols", response_model=list[SymbolInfo])
async def list_symbols(request: Request) -> list[SymbolInfo]:
    """Return all available trading symbols from the connected MT5 terminal."""
    await _ensure_connected(request)
    mt5 = _get_mt5()
    if mt5 is None:
        raise HTTPException(status_code=501, detail="MetaTrader5 not available")

    symbols = mt5.symbols_get()
    if symbols is None:
        return []

    results: list[SymbolInfo] = []
    for s in symbols:
        results.append(SymbolInfo(
            name=s.name,
            description=getattr(s, "description", ""),
            bid=s.bid,
            ask=s.ask,
            spread=s.spread,
            digits=s.digits,
            trade_mode=str(getattr(s, "trade_mode", "")),
        ))
    return results


@router.get("/charts")
async def open_charts(request: Request) -> dict[str, Any]:
    """Return information about the currently open MT5 charts.

    MT5 does not expose a direct 'charts' API, so this returns terminal info
    and the list of visible symbols as a proxy.
    """
    await _ensure_connected(request)
    mt5 = _get_mt5()
    if mt5 is None:
        raise HTTPException(status_code=501, detail="MetaTrader5 not available")

    terminal = mt5.terminal_info()
    if terminal is None:
        return {"charts": [], "terminal": None}

    symbols = mt5.symbols_get()
    visible = [s.name for s in (symbols or []) if getattr(s, "visible", False)]

    return {
        "terminal": {
            "name": terminal.name,
            "path": terminal.path,
            "data_path": terminal.data_path,
            "connected": terminal.connected,
        },
        "visible_symbols": visible,
    }
