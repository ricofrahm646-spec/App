"""
Risk Service — JARVIS AI Trading OS.

Provides two groups of functionality:
  1. DB-backed settings, validation, and emergency-stop management
     (used by FastAPI routes that receive a SQLAlchemy Session).
  2. Pure-calculation helpers (position sizing, drawdown, Sharpe ratio, etc.)
     that operate on raw numbers only — no DB dependency.
"""
import logging
import math
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger as log

try:
    from sqlalchemy.orm import Session
    from app.models.risk_model import RiskEvent, RiskSettings
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False
    Session = None       # type: ignore
    RiskSettings = None  # type: ignore
    RiskEvent = None     # type: ignore


# ---------------------------------------------------------------------------
# Constants — used as defaults throughout the service
# ---------------------------------------------------------------------------

class RiskService:
    """
    Central risk management service for the JARVIS trading system.

    All monetary values are in account currency.
    All percentages expressed as decimals (0.02 = 2 %) unless noted otherwise.
    """

    # Class-level defaults (override via DB settings when available)
    MAX_RISK_PER_TRADE:    float = 0.02   # 2 % per trade
    MAX_DAILY_DRAWDOWN:    float = 0.05   # 5 % daily drawdown
    MAX_TOTAL_DRAWDOWN:    float = 0.20   # 20 % total drawdown
    MAX_CONCURRENT_TRADES: int   = 1
    MIN_RISK_REWARD:       float = 1.5    # Minimum acceptable R:R

    # ==================================================================
    # SECTION A — DB-backed methods (used by API routes)
    # ==================================================================

    @staticmethod
    def get_settings(db: "Session") -> Any:
        """Return (or create) the singleton RiskSettings row."""
        if not _DB_AVAILABLE:
            raise RuntimeError("Database not available")
        settings_obj = db.query(RiskSettings).first()
        if not settings_obj:
            settings_obj = RiskSettings()
            db.add(settings_obj)
            db.commit()
            db.refresh(settings_obj)
        return settings_obj

    @staticmethod
    def update_settings(db: "Session", data: Dict[str, Any]) -> Any:
        """Update allowed RiskSettings fields from *data* and persist."""
        s = RiskService.get_settings(db)
        allowed = {
            "risk_percent_per_trade", "max_daily_loss_percent",
            "max_drawdown_percent", "max_open_trades", "max_lot_size",
            "min_lot_size", "max_spread_points", "allow_hedging",
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
        """
        Calculate lot size (DB-free) and return a full breakdown dict.

        Args:
            account_balance: Current account balance.
            risk_percent:    Percentage of balance to risk (e.g. 2.0 for 2 %).
            stop_loss_pips:  SL distance in pips.
            pip_value:       Monetary value of 1 pip per 1 standard lot.
            lot_step:        Minimum volume increment.
            min_lot / max_lot: Volume bounds.
        """
        if stop_loss_pips <= 0 or pip_value <= 0:
            return {"lot_size": min_lot, "risk_amount": 0,
                    "error": "Invalid SL or pip value"}

        risk_amount = account_balance * risk_percent / 100.0
        raw_lots    = risk_amount / (stop_loss_pips * pip_value)
        lot_size    = math.floor(raw_lots / lot_step) * lot_step
        lot_size    = max(min_lot, min(max_lot, lot_size))

        return {
            "lot_size":        round(lot_size, 2),
            "risk_amount":     round(risk_amount, 2),
            "risk_percent":    risk_percent,
            "stop_loss_pips":  stop_loss_pips,
            "pip_value":       pip_value,
            "account_balance": account_balance,
            "max_loss":        round(lot_size * stop_loss_pips * pip_value, 2),
        }

    @staticmethod
    def validate_trade(
        symbol: str,
        direction: str,
        account_info: Dict,
        open_trades: List[Dict],
        db: Optional["Session"] = None,
    ) -> Dict:
        """
        Validate whether a new trade is permissible under risk rules.

        Accepts either:
          - Spec-style call: validate_trade(symbol, direction, account_info, open_trades)
          - DB-style call  : validate_trade(symbol, direction, account_info, open_trades, db=session)

        Returns:
            {"allowed": bool, "reason": str}
        """
        direction  = direction.upper()
        balance    = account_info.get("balance", 0.0)
        equity     = account_info.get("equity", 0.0)
        margin_lvl = account_info.get("margin_level", 9999.0)

        # Load limits from DB if available, else use class defaults
        max_trades = RiskService.MAX_CONCURRENT_TRADES
        max_dd_pct = RiskService.MAX_TOTAL_DRAWDOWN * 100
        em_stop    = False

        if db and _DB_AVAILABLE:
            try:
                s = RiskService.get_settings(db)
                max_trades = s.max_open_trades
                max_dd_pct = s.max_drawdown_percent
                em_stop    = s.emergency_stop_enabled
            except Exception:
                pass

        if em_stop:
            return {"allowed": False, "reason": "Emergency stop is active. All trading halted."}

        if len(open_trades) >= max_trades:
            return {
                "allowed": False,
                "reason": (
                    f"Max concurrent trades reached ({max_trades}). "
                    f"Currently open: {len(open_trades)}."
                ),
            }

        # No opposing direction on same symbol
        for trade in open_trades:
            if trade.get("symbol", "").upper() == symbol.upper():
                trade_dir = trade.get("type", "").upper()
                if trade_dir and trade_dir != direction:
                    return {
                        "allowed": False,
                        "reason": (
                            f"Opposing {trade_dir} already open for {symbol}. "
                            f"Cannot place {direction}."
                        ),
                    }

        # Total drawdown check
        if balance > 0:
            total_dd_pct = (balance - equity) / balance * 100
            if total_dd_pct >= max_dd_pct:
                return {
                    "allowed": False,
                    "reason": (
                        f"Total drawdown {total_dd_pct:.1f}% exceeds "
                        f"maximum {max_dd_pct:.0f}%."
                    ),
                }

        # Margin level check
        if 0 < margin_lvl < 120.0:
            return {
                "allowed": False,
                "reason": (
                    f"Margin level too low: {margin_lvl:.1f}%. Minimum: 120%."
                ),
            }

        return {"allowed": True, "reason": "Trade parameters within risk limits."}

    @staticmethod
    def get_metrics(
        db: "Session",
        account_balance: float,
        account_equity: float,
        open_positions: list,
        trade_history: list,
    ) -> Dict[str, Any]:
        """Return a dashboard metrics dict based on current account state."""
        s = RiskService.get_settings(db)

        open_profit  = sum(p.get("profit", 0) for p in open_positions)
        open_lots    = sum(p.get("volume", 0) for p in open_positions)
        exposure_pct = (open_lots * 100_000) / (account_balance * 100) * 100 \
                       if account_balance > 0 else 0

        profits = [t.get("profit", 0) for t in trade_history]
        peak, current_dd = account_balance, 0.0
        if profits:
            running = account_balance
            for p in profits:
                running += p
                if running > peak:
                    peak = running
            current_dd = (peak - account_equity) / peak * 100 if peak > 0 else 0

        daily_pnl = sum(profits[:20])

        return {
            "account_balance":     account_balance,
            "account_equity":      account_equity,
            "open_profit":         round(open_profit, 2),
            "open_lots":           round(open_lots, 2),
            "open_trades":         len(open_positions),
            "exposure_pct":        round(exposure_pct, 2),
            "current_drawdown_pct": round(current_dd, 2),
            "daily_pnl":           round(daily_pnl, 2),
            "emergency_stop":      s.emergency_stop_enabled,
            "limits": {
                "max_open_trades":    s.max_open_trades,
                "max_lot_size":       s.max_lot_size,
                "max_daily_loss_pct": s.max_daily_loss_percent,
                "max_drawdown_pct":   s.max_drawdown_percent,
                "risk_per_trade_pct": s.risk_percent_per_trade,
            },
            "status": {
                "daily_loss_breached": daily_pnl < -(account_balance * s.max_daily_loss_percent / 100),
                "drawdown_breached":   current_dd > s.max_drawdown_percent,
                "max_trades_reached":  len(open_positions) >= s.max_open_trades,
            },
        }

    @staticmethod
    def get_drawdown_info(
        account_balance: float,
        account_equity: float,
        trade_history: list,
    ) -> Dict[str, Any]:
        """Compute a detailed drawdown breakdown from trade history."""
        profits       = [t.get("profit", 0) for t in trade_history]
        equity_series = []
        running = peak = account_balance
        max_dd = max_dd_pct = 0.0
        max_dd_start = max_dd_end = 0

        for i, p in enumerate(profits):
            running += p
            equity_series.append(round(running, 2))
            if running > peak:
                peak = running
                max_dd_start = i
            dd     = peak - running
            dd_pct = dd / peak * 100 if peak > 0 else 0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd     = dd
                max_dd_end = i

        current_dd     = peak - account_equity
        current_dd_pct = current_dd / peak * 100 if peak > 0 else 0

        return {
            "current_drawdown":     round(current_dd, 2),
            "current_drawdown_pct": round(current_dd_pct, 2),
            "max_drawdown":         round(max_dd, 2),
            "max_drawdown_pct":     round(max_dd_pct, 2),
            "peak_balance":         round(peak, 2),
            "peak_position":        max_dd_start,
            "trough_position":      max_dd_end,
            "equity_series":        equity_series[-100:],
        }

    @staticmethod
    def trigger_emergency_stop(
        db: "Session", reason: str = "Manual trigger"
    ) -> Dict[str, Any]:
        """Activate the emergency stop and log a CRITICAL risk event."""
        s = RiskService.get_settings(db)
        s.emergency_stop_enabled   = True
        s.emergency_stopped_at     = datetime.utcnow()
        db.commit()

        event = RiskEvent(
            event_type="EMERGENCY_STOP", severity="CRITICAL",
            message=f"Emergency stop triggered: {reason}",
            data={"triggered_at": datetime.utcnow().isoformat(), "reason": reason},
        )
        db.add(event)
        db.commit()

        log.critical("EMERGENCY STOP TRIGGERED: %s", reason)
        return {
            "emergency_stop": True,
            "triggered_at":   s.emergency_stopped_at.isoformat(),
            "reason":         reason,
            "message": "All trading halted. Close positions manually or via the API.",
        }

    @staticmethod
    def release_emergency_stop(db: "Session") -> Dict[str, Any]:
        """Deactivate the emergency stop."""
        s = RiskService.get_settings(db)
        s.emergency_stop_enabled = False
        db.commit()

        event = RiskEvent(
            event_type="EMERGENCY_STOP_RELEASED", severity="INFO",
            message="Emergency stop released",
            data={"released_at": datetime.utcnow().isoformat()},
        )
        db.add(event)
        db.commit()

        log.info("Emergency stop released")
        return {"emergency_stop": False, "message": "Emergency stop released. Trading resumed."}

    # ==================================================================
    # SECTION B — Pure-calculation methods (no DB dependency)
    # ==================================================================

    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        sl_distance_pips: float,
        pip_value: float,
    ) -> float:
        """
        Calculate position size in lots using fixed-fractional risk.

        Args:
            account_balance:  Current balance in account currency.
            risk_percent:     Fraction to risk (e.g. 0.02 = 2 %).
            sl_distance_pips: Stop-loss distance in pips.
            pip_value:        Monetary value of 1 pip per 1 standard lot.

        Returns:
            Lot size rounded to 2 decimal places (min 0.01).
        """
        if sl_distance_pips <= 0 or pip_value <= 0 or account_balance <= 0:
            log.warning(
                f"calculate_position_size: invalid input "
                f"balance={account_balance} sl={sl_distance_pips} pip_val={pip_value}"
            )
            return 0.01

        risk_amount  = account_balance * risk_percent
        loss_per_lot = sl_distance_pips * pip_value
        lots         = risk_amount / loss_per_lot
        return max(0.01, min(100.0, round(lots, 2)))

    def calculate_risk_reward(
        self,
        entry: float,
        sl: float,
        tp: float,
        direction: str,
    ) -> float:
        """
        Calculate the reward-to-risk ratio.

        Returns 0.0 for invalid parameters (e.g. SL/TP on wrong side of entry).
        """
        direction = direction.upper()
        if direction == "BUY":
            risk   = entry - sl
            reward = tp    - entry
        elif direction == "SELL":
            risk   = sl    - entry
            reward = entry - tp
        else:
            log.warning(f"calculate_risk_reward: unknown direction '{direction}'")
            return 0.0

        if risk <= 0 or reward <= 0:
            return 0.0
        return round(reward / risk, 2)

    def calculate_drawdown(self, balance: float, equity: float) -> float:
        """
        Current floating drawdown as a fraction of balance (0.0–1.0).
        """
        if balance <= 0:
            return 0.0
        return round(max(0.0, (balance - equity) / balance), 6)

    def should_stop_trading(
        self,
        balance_start: float,
        current_equity: float,
        trades: List[Dict],
    ) -> Dict:
        """
        Determine whether trading should be halted based on risk thresholds.

        Checks:
        - Total drawdown vs MAX_TOTAL_DRAWDOWN
        - Daily loss vs MAX_DAILY_DRAWDOWN
        - 5+ consecutive losing trades

        Returns: {"stop": bool, "reason": str}
        """
        if balance_start <= 0:
            return {"stop": True, "reason": "Invalid starting balance."}

        total_dd = (balance_start - current_equity) / balance_start
        if total_dd >= self.MAX_TOTAL_DRAWDOWN:
            return {
                "stop": True,
                "reason": (
                    f"Total drawdown {total_dd*100:.1f}% reached the "
                    f"{self.MAX_TOTAL_DRAWDOWN*100:.0f}% limit."
                ),
            }

        today_profit  = sum(t.get("profit", 0.0) for t in trades)
        daily_dd = -today_profit / balance_start if today_profit < 0 else 0.0
        if daily_dd >= self.MAX_DAILY_DRAWDOWN:
            return {
                "stop": True,
                "reason": (
                    f"Daily drawdown {daily_dd*100:.1f}% reached the "
                    f"{self.MAX_DAILY_DRAWDOWN*100:.0f}% daily limit."
                ),
            }

        if len(trades) >= 5:
            last_five = [t.get("profit", 0.0) for t in trades[-5:]]
            if all(p < 0 for p in last_five):
                return {
                    "stop": True,
                    "reason": "5 consecutive losing trades detected. Halted for review.",
                }

        return {"stop": False, "reason": "Risk parameters within safe limits."}

    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """
        Gross profit / gross loss.

        Returns +inf if no losing trades, 0.0 if no winning trades.
        """
        gross_profit = sum(t["profit"] for t in trades if t.get("profit", 0) > 0)
        gross_loss   = abs(sum(t["profit"] for t in trades if t.get("profit", 0) < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return round(gross_profit / gross_loss, 4)

    def calculate_sharpe_ratio(
        self, returns: List[float], risk_free_rate: float = 0.0
    ) -> float:
        """
        Annualised Sharpe Ratio from a list of daily returns.

        Args:
            returns:        Period returns as fractions (e.g. 0.01 = 1 %).
            risk_free_rate: Annual risk-free rate (default 0 %).

        Returns 0.0 if fewer than 2 data points or std dev is zero.
        """
        if len(returns) < 2:
            return 0.0
        mean = statistics.mean(returns)
        std  = statistics.stdev(returns)
        if std == 0:
            return 0.0
        daily_rf = risk_free_rate / 252
        return round((mean - daily_rf) / std * math.sqrt(252), 4)

    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        Maximum peak-to-trough drawdown from an equity curve.

        Returns a fraction (e.g. 0.15 = 15 %).
        """
        if len(equity_curve) < 2:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for equity in equity_curve[1:]:
            if equity > peak:
                peak = equity
            elif peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)
        return round(max_dd, 6)

    def dynamic_risk_adjustment(self, recent_performance: Dict) -> float:
        """
        Return an adjusted risk fraction based on recent trading performance.

        Reduces risk after drawdown or losing streaks.
        Increases risk (up to MAX_RISK_PER_TRADE) after a strong winning streak.

        Args:
            recent_performance: {
                consecutive_wins   (int),
                consecutive_losses (int),
                current_drawdown   (float, fraction),
                win_rate_recent    (float, fraction over last 20 trades),
                profit_factor_recent (float),
            }

        Returns:
            Adjusted risk fraction clamped to [0.005, MAX_RISK_PER_TRADE].
        """
        base     = self.MAX_RISK_PER_TRADE
        adjusted = base

        cons_wins   = recent_performance.get("consecutive_wins",   0)
        cons_losses = recent_performance.get("consecutive_losses",  0)
        drawdown    = recent_performance.get("current_drawdown",   0.0)
        win_rate    = recent_performance.get("win_rate_recent",    0.5)
        pf          = recent_performance.get("profit_factor_recent", 1.0)

        # Drawdown penalty
        if drawdown >= 0.10:
            adjusted *= 0.50
        elif drawdown >= 0.05:
            adjusted *= 0.75

        # Losing streak penalty
        if cons_losses >= 3:
            adjusted *= max(0.25, 1 - 0.15 * cons_losses)

        # Winning streak bonus
        if cons_wins >= 3 and pf > 1.5 and win_rate > 0.6:
            adjusted *= min(1.25, 1 + 0.05 * cons_wins)

        adjusted = round(max(0.005, min(self.MAX_RISK_PER_TRADE, adjusted)), 4)
        log.debug(
            f"dynamic_risk_adjustment: base={base*100:.1f}% → {adjusted*100:.2f}% "
            f"(dd={drawdown*100:.1f}% wins={cons_wins} losses={cons_losses})"
        )
        return adjusted

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def calculate_win_rate(self, trades: List[Dict]) -> float:
        """Return win rate as a fraction (0.0–1.0)."""
        if not trades:
            return 0.0
        winners = sum(1 for t in trades if t.get("profit", 0) > 0)
        return round(winners / len(trades), 4)

    def calculate_expectancy(self, trades: List[Dict]) -> float:
        """
        Mathematical expectancy per trade in account currency.

        E = (win_rate × avg_win) − (loss_rate × avg_loss)
        """
        if not trades:
            return 0.0
        wins   = [t["profit"] for t in trades if t.get("profit", 0) > 0]
        losses = [abs(t["profit"]) for t in trades if t.get("profit", 0) < 0]
        wr     = len(wins) / len(trades)
        avg_w  = statistics.mean(wins)   if wins   else 0.0
        avg_l  = statistics.mean(losses) if losses else 0.0
        return round((wr * avg_w) - ((1 - wr) * avg_l), 4)

    def full_risk_report(
        self,
        account_info: Dict,
        trades: List[Dict],
        equity_curve: List[float],
        returns: List[float],
    ) -> Dict:
        """Generate a comprehensive risk report for the current session."""
        balance = account_info.get("balance", 0.0)
        equity  = account_info.get("equity",  0.0)
        return {
            "current_drawdown_pct": round(self.calculate_drawdown(balance, equity) * 100, 2),
            "max_drawdown_pct":     round(self.calculate_max_drawdown(equity_curve) * 100, 2),
            "profit_factor":        self.calculate_profit_factor(trades),
            "sharpe_ratio":         self.calculate_sharpe_ratio(returns),
            "win_rate_pct":         round(self.calculate_win_rate(trades) * 100, 2),
            "expectancy":           self.calculate_expectancy(trades),
            "total_trades":         len(trades),
            "balance":              balance,
            "equity":               equity,
            "margin_level":         account_info.get("margin_level", 0.0),
        }
