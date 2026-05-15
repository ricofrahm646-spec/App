"""
Dashboard Router - aggregated overview, stats, equity curve, real-time WebSocket.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_mt5
from app.database import get_db
from app.models.backtest import BacktestResult, BacktestStatus
from app.models.strategy import Strategy, StrategyStatus
from app.services.mt5_service import MT5Service
from app.services.risk_service import RiskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ─────────────────────────────────────── Helpers ────────────────────────────

async def _safe_account(mt5: MT5Service) -> Dict[str, Any]:
    try:
        return await mt5.get_account_info()
    except Exception:
        return {"balance": 0, "equity": 0, "profit": 0, "margin": 0, "margin_free": 0, "margin_level": 0, "currency": "USD"}


async def _safe_positions(mt5: MT5Service) -> List[Dict[str, Any]]:
    try:
        return await mt5.get_open_trades()
    except Exception:
        return []


async def _safe_history(mt5: MT5Service, days: int = 30) -> List[Dict[str, Any]]:
    try:
        return await mt5.get_trade_history(days=days)
    except Exception:
        return []


def _compute_stats(history: List[Dict], account: Dict) -> Dict[str, Any]:
    if not history:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate": 0.0, "total_profit": 0.0, "total_loss": 0.0,
            "net_pnl": 0.0, "profit_factor": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
            "best_trade": 0.0, "worst_trade": 0.0,
            "daily_pnl": 0.0, "weekly_pnl": 0.0, "monthly_pnl": 0.0,
        }

    profits = [h.get("profit", 0) for h in history]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    net_pnl = sum(profits)
    pf = round(total_profit / total_loss, 3) if total_loss > 0 else 0.0

    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    def _pnl_since(cutoff: datetime) -> float:
        return sum(
            h.get("profit", 0) for h in history
            if h.get("close_time") and datetime.fromisoformat(str(h["close_time"])) > cutoff
        )

    return {
        "total_trades": len(history),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / len(history) * 100, 1),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "net_pnl": round(net_pnl, 2),
        "profit_factor": pf,
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss": round(abs(sum(losses)) / len(losses), 2) if losses else 0.0,
        "best_trade": round(max(profits), 2),
        "worst_trade": round(min(profits), 2),
        "daily_pnl": round(_pnl_since(day_ago), 2),
        "weekly_pnl": round(_pnl_since(week_ago), 2),
        "monthly_pnl": round(_pnl_since(month_ago), 2),
    }


def _build_equity_curve(history: List[Dict], initial_balance: float) -> List[Dict[str, Any]]:
    if not history:
        return [{"date": datetime.utcnow().strftime("%Y-%m-%d"), "equity": initial_balance}]
    sorted_history = sorted(history, key=lambda x: x.get("close_time") or x.get("time") or "")
    equity = initial_balance
    curve = []
    for deal in sorted_history:
        equity += deal.get("profit", 0)
        date = deal.get("close_time") or deal.get("time") or ""
        curve.append({"date": str(date)[:16], "equity": round(equity, 2)})
    return curve


# ─────────────────────────────────────────────────────── Endpoints ────────────

@router.get("/overview", summary="Full dashboard overview")
async def get_overview(
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """
    Returns a comprehensive snapshot: account, positions, trade stats,
    active strategies, recent backtests, AI status, and risk metrics.
    """
    from app.core.config import settings as cfg
    account = await _safe_account(mt5)
    positions = await _safe_positions(mt5)
    history = await _safe_history(mt5, days=30)
    connected = await mt5.is_connected()

    strategies = db.query(Strategy).all()
    active_strategies = [s for s in strategies if s.status == StrategyStatus.ACTIVE]

    recent_backtests = (
        db.query(BacktestResult)
        .filter(BacktestResult.status == BacktestStatus.COMPLETED)
        .order_by(BacktestResult.created_at.desc())
        .limit(5)
        .all()
    )

    stats = _compute_stats(history, account)
    risk = RiskService.get_metrics(
        db,
        account_balance=account.get("balance", 0),
        account_equity=account.get("equity", 0),
        open_positions=positions,
        trade_history=history,
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "account": account,
        "mt5_connected": connected,
        "positions": {
            "count": len(positions),
            "open_profit": round(sum(p.get("profit", 0) for p in positions), 2),
            "items": positions,
        },
        "trades": stats,
        "strategies": {
            "total": len(strategies),
            "active": len(active_strategies),
            "active_list": [{"id": s.id, "name": s.name, "type": s.type} for s in active_strategies],
        },
        "backtests": {
            "total": db.query(BacktestResult).count(),
            "recent": [
                {
                    "id": b.id,
                    "strategy_name": b.strategy_name,
                    "symbol": b.symbol,
                    "total_return_pct": b.total_return_pct,
                    "win_rate": b.win_rate,
                    "completed_at": b.completed_at.isoformat() if b.completed_at else None,
                }
                for b in recent_backtests
            ],
        },
        "risk": risk,
        "ai_status": {
            "openai_configured": bool(cfg.OPENAI_API_KEY),
            "anthropic_configured": bool(cfg.ANTHROPIC_API_KEY),
        },
    }


@router.get("/stats", summary="Trading statistics summary")
async def get_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Return aggregated trading statistics for the last N days."""
    account = await _safe_account(mt5)
    history = await _safe_history(mt5, days=days)
    return {
        "period_days": days,
        "stats": _compute_stats(history, account),
        "account_balance": account.get("balance", 0),
        "account_equity": account.get("equity", 0),
    }


@router.get("/equity-curve", summary="Equity curve data points")
async def get_equity_curve(
    days: int = 90,
    db: Session = Depends(get_db),
    mt5: MT5Service = Depends(get_mt5),
) -> List[Dict[str, Any]]:
    """Return chronological equity curve points reconstructed from closed trades."""
    account = await _safe_account(mt5)
    history = await _safe_history(mt5, days=days)
    initial = account.get("balance", 10000.0) - sum(h.get("profit", 0) for h in history)
    return _build_equity_curve(history, initial)


@router.get("/performance", summary="Performance breakdown by symbol")
async def get_performance(
    days: int = 30,
    mt5: MT5Service = Depends(get_mt5),
) -> Dict[str, Any]:
    """Return performance breakdown grouped by symbol."""
    history = await _safe_history(mt5, days=days)
    by_symbol: Dict[str, Dict] = {}
    for deal in history:
        sym = deal.get("symbol", "UNKNOWN")
        if sym not in by_symbol:
            by_symbol[sym] = {"symbol": sym, "trades": 0, "profit": 0.0, "wins": 0}
        by_symbol[sym]["trades"] += 1
        p = deal.get("profit", 0)
        by_symbol[sym]["profit"] = round(by_symbol[sym]["profit"] + p, 2)
        if p > 0:
            by_symbol[sym]["wins"] += 1
    for sym in by_symbol:
        d = by_symbol[sym]
        d["win_rate"] = round(d["wins"] / d["trades"] * 100, 1) if d["trades"] > 0 else 0.0
    return {
        "period_days": days,
        "by_symbol": list(by_symbol.values()),
        "best_symbol": max(by_symbol.values(), key=lambda x: x["profit"])["symbol"] if by_symbol else None,
    }


@router.get("/market-analysis", summary="Current market analysis snapshot")
async def get_market_analysis(mt5: MT5Service = Depends(get_mt5)) -> Dict[str, Any]:
    """Return live prices for key trading pairs."""
    pairs = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
    connected = await mt5.is_connected()
    market_data = []
    for pair in pairs:
        try:
            price = await mt5.get_current_price(pair)
            market_data.append({
                "symbol": pair,
                "bid": price.get("bid"),
                "ask": price.get("ask"),
                "spread": round((price.get("ask", 0) - price.get("bid", 0)) * 10000, 1),
            })
        except Exception:
            market_data.append({"symbol": pair, "bid": None, "ask": None, "error": "unavailable"})

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "mt5_connected": connected,
        "market_data": market_data,
    }


@router.websocket("/ws")
async def dashboard_ws(
    websocket: WebSocket,
    mt5: MT5Service = Depends(get_mt5),
) -> None:
    """
    Real-time dashboard WebSocket.
    Pushes a full account/positions snapshot every second.
    """
    await websocket.accept()
    logger.info("Dashboard WebSocket connected")

    async def push_update() -> None:
        account = await _safe_account(mt5)
        positions = await _safe_positions(mt5)
        connected = await mt5.is_connected()
        await websocket.send_json({
            "type": "update",
            "timestamp": datetime.utcnow().isoformat(),
            "account": {
                "balance": account.get("balance"),
                "equity": account.get("equity"),
                "profit": account.get("profit"),
                "margin_level": account.get("margin_level"),
            },
            "positions": {
                "count": len(positions),
                "open_profit": round(sum(p.get("profit", 0) for p in positions), 2),
            },
            "mt5_connected": connected,
        })

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                msg = json.loads(raw)
                if msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                elif msg.get("action") == "stop":
                    break
                else:
                    await push_update()
            except asyncio.TimeoutError:
                await push_update()
            except (json.JSONDecodeError, KeyError):
                await push_update()
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
    except Exception as exc:
        logger.exception("Dashboard WebSocket error: %s", exc)
