from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Query, status

from app.models.schemas import (
    APIResponse,
    AccountInfo,
    DashboardData,
    OrderSide,
    OrderType,
    OrderStatus,
    PaginatedResponse,
    PerformanceMetrics,
    PositionResponse,
    TradeHistoryQuery,
    TradeResponse,
)

logger = structlog.get_logger("jarvis.dashboard")
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _seed_rng() -> random.Random:
    return random.Random(42)


def _build_account() -> AccountInfo:
    return AccountInfo(
        login=12345678,
        name="JARVIS Demo",
        server="MetaQuotes-Demo",
        currency="USD",
        balance=12450.75,
        equity=12580.30,
        margin=1200.00,
        free_margin=11380.30,
        margin_level=1048.36,
        leverage=100,
        profit=129.55,
        connected=True,
    )


def _build_performance() -> PerformanceMetrics:
    return PerformanceMetrics(
        daily_pnl=85.20,
        weekly_pnl=320.50,
        monthly_pnl=1250.75,
        total_pnl=2450.75,
        daily_pnl_pct=0.68,
        weekly_pnl_pct=2.61,
        monthly_pnl_pct=11.16,
        total_pnl_pct=24.51,
        win_rate=62.5,
        profit_factor=1.85,
        total_trades=156,
        avg_trade=15.71,
        best_trade=245.30,
        worst_trade=-120.50,
        max_drawdown=450.25,
        max_drawdown_pct=3.58,
        sharpe_ratio=1.92,
    )


def _build_sample_trades(count: int = 20) -> list[TradeResponse]:
    rng = _seed_rng()
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "GBPJPY"]
    trades: list[TradeResponse] = []
    now = datetime.now(timezone.utc)

    for i in range(count):
        sym = rng.choice(symbols)
        side = OrderSide.BUY if rng.random() > 0.5 else OrderSide.SELL
        price = round(rng.uniform(1.05, 1.15) if "USD" in sym[:3] else rng.uniform(140, 195), 5)
        profit = round(rng.gauss(15, 60), 2)
        open_time = now - timedelta(hours=rng.randint(1, 720))
        close_time = open_time + timedelta(minutes=rng.randint(15, 480))

        trades.append(
            TradeResponse(
                ticket=100001 + i,
                symbol=sym,
                side=side,
                order_type=OrderType.MARKET,
                volume=round(rng.choice([0.01, 0.05, 0.1, 0.2, 0.5]), 2),
                open_price=price,
                close_price=round(
                    price + profit * 0.0001 * (1 if side == OrderSide.BUY else -1), 5
                ),
                stop_loss=round(price - 0.003 * (1 if side == OrderSide.BUY else -1), 5),
                take_profit=round(price + 0.006 * (1 if side == OrderSide.BUY else -1), 5),
                profit=profit,
                commission=round(rng.uniform(0.5, 3.0), 2),
                swap=round(rng.uniform(-2, 2), 2),
                open_time=open_time,
                close_time=close_time,
                magic_number=123456,
                comment="JARVIS",
                status=OrderStatus.FILLED,
            )
        )
    return sorted(trades, key=lambda t: t.open_time, reverse=True)


def _build_equity_history(days: int = 30) -> list[dict[str, Any]]:
    rng = _seed_rng()
    equity = 10000.0
    history: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for d in range(days, 0, -1):
        equity += rng.gauss(30, 80)
        history.append({
            "date": (now - timedelta(days=d)).isoformat(),
            "equity": round(equity, 2),
            "balance": round(equity - rng.uniform(-50, 50), 2),
        })
    return history


# ── Full dashboard snapshot ──────────────────────────────────────────────

@router.get(
    "",
    response_model=APIResponse,
    summary="Get full dashboard data",
)
async def get_dashboard() -> APIResponse:
    trades = _build_sample_trades(20)
    positions = [
        PositionResponse(
            ticket=200001,
            symbol="EURUSD",
            side=OrderSide.BUY,
            volume=0.1,
            open_price=1.08750,
            current_price=1.08920,
            stop_loss=1.08500,
            take_profit=1.09200,
            profit=17.00,
            open_time=datetime.now(timezone.utc) - timedelta(hours=3),
        ),
        PositionResponse(
            ticket=200002,
            symbol="XAUUSD",
            side=OrderSide.SELL,
            volume=0.05,
            open_price=2345.50,
            current_price=2342.80,
            stop_loss=2355.00,
            take_profit=2330.00,
            profit=13.50,
            open_time=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
    ]

    dashboard = DashboardData(
        account=_build_account(),
        performance=_build_performance(),
        open_positions=positions,
        recent_trades=trades[:10],
        equity_history=_build_equity_history(30),
        pnl_by_symbol={
            "EURUSD": 520.30,
            "GBPUSD": 310.50,
            "USDJPY": -85.20,
            "XAUUSD": 890.15,
            "GBPJPY": -45.00,
        },
        pnl_by_day=[
            {"day": "Mon", "pnl": 125.30},
            {"day": "Tue", "pnl": -45.20},
            {"day": "Wed", "pnl": 210.50},
            {"day": "Thu", "pnl": 85.60},
            {"day": "Fri", "pnl": -55.70},
        ],
    )
    return APIResponse(success=True, data=dashboard.model_dump(mode="json"))


# ── Account stats ────────────────────────────────────────────────────────

@router.get(
    "/account",
    response_model=APIResponse,
    summary="Get account statistics",
)
async def get_account_stats() -> APIResponse:
    return APIResponse(
        success=True, data=_build_account().model_dump(mode="json")
    )


# ── Performance metrics ─────────────────────────────────────────────────

@router.get(
    "/performance",
    response_model=APIResponse,
    summary="Get performance metrics",
)
async def get_performance(
    period: str = Query(
        default="all",
        description="Period filter: today, week, month, all",
    ),
) -> APIResponse:
    perf = _build_performance()
    return APIResponse(success=True, data=perf.model_dump(mode="json"))


# ── Trade history ────────────────────────────────────────────────────────

@router.get(
    "/trades",
    response_model=APIResponse,
    summary="Get paginated trade history",
)
async def get_trade_history(
    symbol: str | None = Query(default=None),
    side: OrderSide | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> APIResponse:
    trades = _build_sample_trades(80)

    if symbol:
        trades = [t for t in trades if t.symbol == symbol.upper()]
    if side:
        trades = [t for t in trades if t.side == side]
    if start_date:
        trades = [t for t in trades if t.open_time >= start_date]
    if end_date:
        trades = [t for t in trades if t.open_time <= end_date]

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


# ── Equity history ───────────────────────────────────────────────────────

@router.get(
    "/equity",
    response_model=APIResponse,
    summary="Get equity curve history",
)
async def get_equity_history(
    days: int = Query(default=30, ge=1, le=365),
) -> APIResponse:
    return APIResponse(success=True, data=_build_equity_history(days))
