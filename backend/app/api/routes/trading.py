from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    APIResponse,
    AccountInfo,
    CloseTradeRequest,
    ModifyTradeRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    PaginatedResponse,
    PositionResponse,
    TradeRequest,
    TradeResponse,
)

logger = structlog.get_logger("jarvis.trading")
router = APIRouter(prefix="/trading", tags=["Trading"])

_positions: dict[int, PositionResponse] = {}
_trade_history: list[TradeResponse] = []
_ticket_counter: int = 100000


def _next_ticket() -> int:
    global _ticket_counter
    _ticket_counter += 1
    return _ticket_counter


# ── Open order ───────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a new trade order",
)
async def open_order(request: TradeRequest) -> APIResponse:
    logger.info(
        "open_order_request",
        symbol=request.symbol,
        side=request.side.value,
        volume=request.volume,
        order_type=request.order_type.value,
    )

    if request.order_type != OrderType.MARKET and request.price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price is required for non-market orders.",
        )

    if request.stop_loss and request.take_profit:
        if request.side == OrderSide.BUY and request.stop_loss >= request.take_profit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For BUY orders stop_loss must be below take_profit.",
            )
        if request.side == OrderSide.SELL and request.stop_loss <= request.take_profit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For SELL orders stop_loss must be above take_profit.",
            )

    ticket = _next_ticket()
    simulated_price = request.price or 1.10000
    now = datetime.now(timezone.utc)

    position = PositionResponse(
        ticket=ticket,
        symbol=request.symbol,
        side=request.side,
        volume=request.volume,
        open_price=simulated_price,
        current_price=simulated_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        open_time=now,
        magic_number=request.magic_number,
        comment=request.comment,
    )
    _positions[ticket] = position

    trade = TradeResponse(
        ticket=ticket,
        symbol=request.symbol,
        side=request.side,
        order_type=request.order_type,
        volume=request.volume,
        open_price=simulated_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        open_time=now,
        magic_number=request.magic_number,
        comment=request.comment,
        status=OrderStatus.FILLED,
    )
    _trade_history.append(trade)

    logger.info("order_opened", ticket=ticket, symbol=request.symbol)
    return APIResponse(
        success=True,
        message=f"Order opened – ticket {ticket}",
        data=trade.model_dump(mode="json"),
    )


# ── Close order ──────────────────────────────────────────────────────────

@router.post(
    "/orders/close",
    response_model=APIResponse,
    summary="Close an open position",
)
async def close_order(request: CloseTradeRequest) -> APIResponse:
    position = _positions.get(request.ticket)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position with ticket {request.ticket} not found.",
        )

    close_volume = request.volume or position.volume
    if close_volume > position.volume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Close volume exceeds position volume.",
        )

    now = datetime.now(timezone.utc)
    close_price = position.current_price

    if close_volume >= position.volume:
        del _positions[request.ticket]
    else:
        _positions[request.ticket] = position.model_copy(
            update={"volume": position.volume - close_volume}
        )

    trade = TradeResponse(
        ticket=position.ticket,
        symbol=position.symbol,
        side=position.side,
        order_type=OrderType.MARKET,
        volume=close_volume,
        open_price=position.open_price,
        close_price=close_price,
        stop_loss=position.stop_loss,
        take_profit=position.take_profit,
        open_time=position.open_time,
        close_time=now,
        profit=0.0,
        status=OrderStatus.FILLED,
    )
    _trade_history.append(trade)

    logger.info("order_closed", ticket=request.ticket)
    return APIResponse(
        success=True,
        message=f"Position {request.ticket} closed.",
        data=trade.model_dump(mode="json"),
    )


# ── Modify order ─────────────────────────────────────────────────────────

@router.put(
    "/orders/{ticket}",
    response_model=APIResponse,
    summary="Modify SL/TP of an open position",
)
async def modify_order(ticket: int, request: ModifyTradeRequest) -> APIResponse:
    position = _positions.get(ticket)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position with ticket {ticket} not found.",
        )

    updates: dict[str, Any] = {}
    if request.stop_loss is not None:
        updates["stop_loss"] = request.stop_loss
    if request.take_profit is not None:
        updates["take_profit"] = request.take_profit

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No modification parameters provided.",
        )

    _positions[ticket] = position.model_copy(update=updates)
    logger.info("order_modified", ticket=ticket, updates=updates)
    return APIResponse(
        success=True,
        message=f"Position {ticket} modified.",
        data=_positions[ticket].model_dump(mode="json"),
    )


# ── Positions ────────────────────────────────────────────────────────────

@router.get(
    "/positions",
    response_model=APIResponse,
    summary="Get all open positions",
)
async def get_positions(
    symbol: str | None = Query(default=None, description="Filter by symbol"),
) -> APIResponse:
    positions = list(_positions.values())
    if symbol:
        positions = [p for p in positions if p.symbol == symbol.upper()]
    return APIResponse(
        success=True,
        message=f"{len(positions)} open position(s).",
        data=[p.model_dump(mode="json") for p in positions],
    )


# ── Trade history ────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=APIResponse,
    summary="Get trade history",
)
async def get_trade_history(
    symbol: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> APIResponse:
    trades = _trade_history[:]
    if symbol:
        trades = [t for t in trades if t.symbol == symbol.upper()]

    total = len(trades)
    start = (page - 1) * page_size
    paginated = trades[start : start + page_size]

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[t.model_dump(mode="json") for t in paginated],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        ).model_dump(mode="json"),
    )


# ── Account info ─────────────────────────────────────────────────────────

@router.get(
    "/account",
    response_model=APIResponse,
    summary="Get MT5 account information",
)
async def get_account_info() -> APIResponse:
    total_profit = sum(p.profit for p in _positions.values())
    account = AccountInfo(
        login=12345678,
        name="JARVIS Demo",
        server="MetaQuotes-Demo",
        currency="USD",
        balance=10000.0,
        equity=10000.0 + total_profit,
        margin=sum(p.volume * 1000 for p in _positions.values()),
        free_margin=10000.0 + total_profit - sum(p.volume * 1000 for p in _positions.values()),
        margin_level=999.99 if _positions else 0.0,
        leverage=100,
        profit=total_profit,
        connected=True,
    )
    return APIResponse(success=True, data=account.model_dump(mode="json"))
