"""
Risk Service - calculates position sizes, validates trades, monitors drawdown.
"""
import logging
import math
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.risk_model import RiskEvent, RiskSettings

logger = logging.getLogger(__name__)


class RiskService:

    @staticmethod
    def get_settings(db: Session) -> RiskSettings:
        settings_obj = db.query(RiskSettings).first()
        if not settings_obj:
            settings_obj = RiskSettings()
            db.add(settings_obj)
            db.commit()
            db.refresh(settings_obj)
        return settings_obj

    @staticmethod
    def update_settings(db: Session, data: Dict[str, Any]) -> RiskSettings:
        s = RiskService.get_settings(db)
        allowed = {
            "risk_percent_per_trade", "max_daily_loss_percent", "max_drawdown_percent",
            "max_open_trades", "max_lot_size", "min_lot_size", "max_spread_points", "allow_hedging",
        }
        for k, v in data.items():
            if k in allowed:
                setattr(s, k, v)
        s.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(s)
        return s

    @staticmethod
    def calculate_lot_size(
        account_balance: float,
        risk_percent: float,
        stop_loss_pips: float,
        pip_value: float = 1.0,
        lot_step: float = 0.01,
        min_lot: float = 0.01,
        max_lot: float = 100.0,
    ) -> Dict[str, Any]:
        if stop_loss_pips <= 0 or pip_value <= 0:
            return {"lot_size": min_lot, "risk_amount": 0, "error": "Invalid SL or pip value"}

        risk_amount = account_balance * risk_percent / 100.0
        raw_lots = risk_amount / (stop_loss_pips * pip_value)
        lot_size = math.floor(raw_lots / lot_step) * lot_step
        lot_size = max(min_lot, min(max_lot, lot_size))

        return {
            "lot_size": round(lot_size, 2),
            "risk_amount": round(risk_amount, 2),
            "risk_percent": risk_percent,
            "stop_loss_pips": stop_loss_pips,
            "pip_value": pip_value,
            "account_balance": account_balance,
            "max_loss": round(lot_size * stop_loss_pips * pip_value, 2),
        }

    @staticmethod
    def validate_trade(
        db: Session,
        symbol: str,
        order_type: str,
        lot_size: float,
        stop_loss: float,
        take_profit: float,
        current_price: float,
        account_equity: float,
        open_trades_count: int,
    ) -> Dict[str, Any]:
        s = RiskService.get_settings(db)
        issues = []
        warnings = []

        if s.emergency_stop_enabled:
            issues.append("Emergency stop is active. All trading is halted.")

        if lot_size > s.max_lot_size:
            issues.append(f"Lot size {lot_size} exceeds max allowed {s.max_lot_size}")
        if lot_size < s.min_lot_size:
            issues.append(f"Lot size {lot_size} below min {s.min_lot_size}")
        if open_trades_count >= s.max_open_trades:
            issues.append(f"Max open trades limit reached ({s.max_open_trades})")

        if stop_loss > 0 and take_profit > 0:
            if order_type.upper() == "BUY":
                sl_pips = (current_price - stop_loss) / 0.0001
                tp_pips = (take_profit - current_price) / 0.0001
            else:
                sl_pips = (stop_loss - current_price) / 0.0001
                tp_pips = (current_price - take_profit) / 0.0001
            if sl_pips > 0 and tp_pips > 0:
                rr = tp_pips / sl_pips
                if rr < 1.0:
                    warnings.append(f"Risk/Reward ratio {rr:.2f} is below 1:1")
        elif stop_loss == 0:
            warnings.append("No stop loss set – high risk trade")

        risk_pct = (lot_size * 100000 * 0.0001 * 30) / account_equity * 100 if account_equity > 0 else 0
        if risk_pct > s.risk_percent_per_trade * 2:
            warnings.append(f"Estimated risk {risk_pct:.1f}% is high relative to settings")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "settings_applied": {
                "max_lot_size": s.max_lot_size,
                "max_open_trades": s.max_open_trades,
                "emergency_stop": s.emergency_stop_enabled,
            },
        }

    @staticmethod
    def get_metrics(
        db: Session,
        account_balance: float,
        account_equity: float,
        open_positions: list,
        trade_history: list,
    ) -> Dict[str, Any]:
        s = RiskService.get_settings(db)

        open_profit = sum(p.get("profit", 0) for p in open_positions)
        open_lots = sum(p.get("volume", 0) for p in open_positions)
        exposure_pct = (open_lots * 100000) / (account_balance * 100) * 100 if account_balance > 0 else 0

        profits = [t.get("profit", 0) for t in trade_history]
        peak = account_balance
        current_dd = 0.0
        if profits:
            running = account_balance
            for p in profits:
                running += p
                if running > peak:
                    peak = running
            current_dd = (peak - account_equity) / peak * 100 if peak > 0 else 0

        daily_pnl = sum(p for p in profits[:20])

        return {
            "account_balance": account_balance,
            "account_equity": account_equity,
            "open_profit": round(open_profit, 2),
            "open_lots": round(open_lots, 2),
            "open_trades": len(open_positions),
            "exposure_pct": round(exposure_pct, 2),
            "current_drawdown_pct": round(current_dd, 2),
            "daily_pnl": round(daily_pnl, 2),
            "emergency_stop": s.emergency_stop_enabled,
            "limits": {
                "max_open_trades": s.max_open_trades,
                "max_lot_size": s.max_lot_size,
                "max_daily_loss_pct": s.max_daily_loss_percent,
                "max_drawdown_pct": s.max_drawdown_percent,
                "risk_per_trade_pct": s.risk_percent_per_trade,
            },
            "status": {
                "daily_loss_breached": daily_pnl < -(account_balance * s.max_daily_loss_percent / 100),
                "drawdown_breached": current_dd > s.max_drawdown_percent,
                "max_trades_reached": len(open_positions) >= s.max_open_trades,
            },
        }

    @staticmethod
    def get_drawdown_info(
        account_balance: float,
        account_equity: float,
        trade_history: list,
    ) -> Dict[str, Any]:
        profits = [t.get("profit", 0) for t in trade_history]
        equity_series = []
        running = account_balance
        peak = account_balance
        max_dd = 0.0
        max_dd_pct = 0.0
        max_dd_start = 0
        max_dd_end = 0

        for i, p in enumerate(profits):
            running += p
            equity_series.append(round(running, 2))
            if running > peak:
                peak = running
                max_dd_start = i
            dd = peak - running
            dd_pct = dd / peak * 100 if peak > 0 else 0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd = dd
                max_dd_end = i

        current_dd = peak - account_equity
        current_dd_pct = current_dd / peak * 100 if peak > 0 else 0

        return {
            "current_drawdown": round(current_dd, 2),
            "current_drawdown_pct": round(current_dd_pct, 2),
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "peak_balance": round(peak, 2),
            "peak_position": max_dd_start,
            "trough_position": max_dd_end,
            "equity_series": equity_series[-100:],
        }

    @staticmethod
    def trigger_emergency_stop(db: Session, reason: str = "Manual trigger") -> Dict[str, Any]:
        s = RiskService.get_settings(db)
        s.emergency_stop_enabled = True
        s.emergency_stopped_at = datetime.utcnow()
        db.commit()

        event = RiskEvent(
            event_type="EMERGENCY_STOP",
            severity="CRITICAL",
            message=f"Emergency stop triggered: {reason}",
            data={"triggered_at": datetime.utcnow().isoformat(), "reason": reason},
        )
        db.add(event)
        db.commit()

        logger.critical("EMERGENCY STOP TRIGGERED: %s", reason)
        return {
            "emergency_stop": True,
            "triggered_at": s.emergency_stopped_at.isoformat(),
            "reason": reason,
            "message": "All trading halted. Close positions manually or via the API.",
        }

    @staticmethod
    def release_emergency_stop(db: Session) -> Dict[str, Any]:
        s = RiskService.get_settings(db)
        s.emergency_stop_enabled = False
        db.commit()

        event = RiskEvent(
            event_type="EMERGENCY_STOP_RELEASED",
            severity="INFO",
            message="Emergency stop released",
            data={"released_at": datetime.utcnow().isoformat()},
        )
        db.add(event)
        db.commit()

        logger.info("Emergency stop released")
        return {"emergency_stop": False, "message": "Emergency stop released. Trading resumed."}
