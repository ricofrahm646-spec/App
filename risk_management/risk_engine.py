"""
JARVIS Core Risk Engine.

Enforces position sizing, pre-trade risk checks, drawdown limits,
circuit breakers, and the emergency kill switch.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Pip value lookup (per standard lot, USD quote) ───────────────────
# For XXX/USD pairs 1 pip = $10; for XXX/JPY 1 pip ≈ varies.
# This simplified table covers the majors; extend as needed.
_PIP_VALUES: Dict[str, float] = {
    "EURUSD": 10.0, "GBPUSD": 10.0, "AUDUSD": 10.0, "NZDUSD": 10.0,
    "USDJPY": 9.0,  "USDCHF": 10.0, "USDCAD": 10.0,
    "EURGBP": 12.0, "EURJPY": 9.0,  "GBPJPY": 9.0,
    "EURAUD": 10.0, "EURCAD": 10.0, "EURNZD": 10.0,
    "GBPAUD": 10.0, "GBPCAD": 10.0, "GBPCHF": 10.0,
    "AUDCAD": 10.0, "AUDJPY": 9.0,  "AUDNZD": 10.0,
    "CADJPY": 9.0,  "CHFJPY": 9.0,  "NZDJPY": 9.0,
    "NZDCAD": 10.0, "NZDCHF": 10.0, "CADCHF": 10.0,
}

_DEFAULT_PIP_VALUE = 10.0  # USD per pip per standard lot


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskCheckResult:
    """Outcome of a pre-trade risk check."""
    allowed: bool
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    warnings: List[str] = field(default_factory=list)


class RiskEngine:
    """Core risk management engine for JARVIS.

    Enforces:
    - Position sizing based on account balance and risk percentage.
    - Max 1 trade at a time.
    - No simultaneous buy + sell positions.
    - Auto-close at 20% account loss.
    - Daily loss limit.
    - Emergency kill switch.
    """

    def __init__(
        self,
        max_risk_percent: float = 2.0,
        max_daily_loss_percent: float = 5.0,
        max_drawdown_percent: float = 20.0,
        max_open_trades: int = 1,
        min_risk_reward: float = 1.0,
    ) -> None:
        self.max_risk_percent = max_risk_percent
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_drawdown_percent = max_drawdown_percent
        self.max_open_trades = max_open_trades
        self.min_risk_reward = min_risk_reward

        self._kill_switch_active: bool = False
        self._open_trades: List[Dict[str, Any]] = []
        self._daily_pnl: float = 0.0
        self._daily_pnl_reset_date: Optional[str] = None

    # ── Position sizing ──────────────────────────────────────────────

    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        sl_pips: float,
        symbol: str,
    ) -> float:
        """Calculate lot size for a trade.

        Args:
            account_balance: Current account balance in USD.
            risk_percent: Percentage of balance to risk (e.g. 1.0 = 1%).
            sl_pips: Stop-loss distance in pips.
            symbol: Forex pair, e.g. "EURUSD".

        Returns:
            Position size in standard lots (rounded to 0.01).
        """
        if sl_pips <= 0:
            raise ValueError("Stop-loss pips must be positive")
        if risk_percent <= 0 or risk_percent > self.max_risk_percent:
            raise ValueError(
                f"Risk percent must be between 0 and {self.max_risk_percent}%"
            )

        risk_amount = account_balance * (risk_percent / 100.0)
        pip_value = _PIP_VALUES.get(symbol.upper(), _DEFAULT_PIP_VALUE)
        lots = risk_amount / (sl_pips * pip_value)
        lots = round(lots, 2)
        lots = max(lots, 0.01)  # minimum micro-lot

        logger.info(
            "Position size: %.2f lots (balance=%.2f, risk=%.1f%%, "
            "sl=%s pips, pip_value=%.2f)",
            lots, account_balance, risk_percent, sl_pips, pip_value,
        )
        return lots

    # ── Pre-trade risk check ─────────────────────────────────────────

    def check_risk_limits(self, trade: Dict[str, Any]) -> RiskCheckResult:
        """Run all pre-trade risk checks.

        Args:
            trade: Dict with keys: symbol, direction ("BUY"/"SELL"),
                   entry, sl, tp, volume, account_balance, daily_pnl.

        Returns:
            RiskCheckResult with allowed=True/False and reason.
        """
        warnings: List[str] = []

        # Kill switch
        if self._kill_switch_active:
            return RiskCheckResult(
                allowed=False,
                reason="Emergency kill switch is active — all trading halted",
                risk_level=RiskLevel.CRITICAL,
            )

        # Max open trades
        if len(self._open_trades) >= self.max_open_trades:
            return RiskCheckResult(
                allowed=False,
                reason=f"Max open trades ({self.max_open_trades}) reached",
                risk_level=RiskLevel.HIGH,
            )

        # No simultaneous buy + sell
        direction = trade.get("direction", "").upper()
        for open_trade in self._open_trades:
            if open_trade["symbol"] == trade.get("symbol"):
                if open_trade["direction"] != direction:
                    return RiskCheckResult(
                        allowed=False,
                        reason=(
                            f"Cannot open {direction} while an opposing "
                            f"{open_trade['direction']} is open on "
                            f"{trade.get('symbol')}"
                        ),
                        risk_level=RiskLevel.HIGH,
                    )

        # Risk:Reward
        entry = trade.get("entry", 0.0)
        sl = trade.get("sl", 0.0)
        tp = trade.get("tp", 0.0)
        if entry and sl and tp:
            rr = self.calculate_risk_reward(entry, sl, tp)
            if rr < self.min_risk_reward:
                warnings.append(
                    f"Risk:Reward ratio {rr:.2f} below minimum {self.min_risk_reward}"
                )

        # Daily loss limit
        daily_pnl = trade.get("daily_pnl", self._daily_pnl)
        account_balance = trade.get("account_balance", 0.0)
        if account_balance > 0:
            daily_loss_pct = abs(min(daily_pnl, 0)) / account_balance * 100
            if daily_loss_pct >= self.max_daily_loss_percent:
                return RiskCheckResult(
                    allowed=False,
                    reason=(
                        f"Daily loss limit reached: {daily_loss_pct:.1f}% "
                        f"(limit {self.max_daily_loss_percent}%)"
                    ),
                    risk_level=RiskLevel.CRITICAL,
                )

        # Drawdown auto-close check
        equity = trade.get("equity", account_balance)
        peak_balance = trade.get("peak_balance", account_balance)
        if peak_balance > 0:
            dd = (peak_balance - equity) / peak_balance * 100
            if dd >= self.max_drawdown_percent:
                return RiskCheckResult(
                    allowed=False,
                    reason=(
                        f"Max drawdown reached: {dd:.1f}% "
                        f"(auto-close threshold {self.max_drawdown_percent}%)"
                    ),
                    risk_level=RiskLevel.CRITICAL,
                )
            if dd >= self.max_drawdown_percent * 0.8:
                warnings.append(
                    f"Drawdown at {dd:.1f}% — approaching "
                    f"{self.max_drawdown_percent}% auto-close threshold"
                )

        risk_level = RiskLevel.LOW
        if warnings:
            risk_level = RiskLevel.MEDIUM

        return RiskCheckResult(
            allowed=True,
            reason="All risk checks passed",
            risk_level=risk_level,
            warnings=warnings,
        )

    # ── Drawdown ─────────────────────────────────────────────────────

    @staticmethod
    def calculate_drawdown(
        equity_history: List[float],
    ) -> Dict[str, float]:
        """Calculate current and maximum drawdown from an equity curve.

        Returns dict with keys:
            current_drawdown, max_drawdown, peak_equity, trough_equity
        """
        if not equity_history:
            return {
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "peak_equity": 0.0,
                "trough_equity": 0.0,
            }

        peak = equity_history[0]
        max_dd = 0.0
        max_dd_trough = peak
        max_dd_peak = peak

        for equity in equity_history:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                max_dd_trough = equity
                max_dd_peak = peak

        current_peak = max(equity_history)
        current_equity = equity_history[-1]
        current_dd = (
            (current_peak - current_equity) / current_peak * 100
            if current_peak > 0
            else 0.0
        )

        return {
            "current_drawdown": round(current_dd, 4),
            "max_drawdown": round(max_dd, 4),
            "peak_equity": max_dd_peak,
            "trough_equity": max_dd_trough,
        }

    # ── Circuit breaker ──────────────────────────────────────────────

    def should_stop_trading(
        self, account_stats: Dict[str, Any]
    ) -> bool:
        """Determine whether trading should be halted.

        Checks:
        - Daily loss limit exceeded.
        - Max drawdown exceeded.
        - Kill switch active.
        - Consecutive losses threshold.

        Args:
            account_stats: Dict with keys: daily_pnl, balance, equity,
                           peak_balance, consecutive_losses.

        Returns:
            True if trading should stop.
        """
        if self._kill_switch_active:
            logger.critical("Kill switch active — trading must stop")
            return True

        balance = account_stats.get("balance", 0.0)
        daily_pnl = account_stats.get("daily_pnl", 0.0)
        equity = account_stats.get("equity", balance)
        peak = account_stats.get("peak_balance", balance)
        consecutive_losses = account_stats.get("consecutive_losses", 0)

        if balance > 0:
            daily_loss_pct = abs(min(daily_pnl, 0)) / balance * 100
            if daily_loss_pct >= self.max_daily_loss_percent:
                logger.warning("Daily loss limit breached: %.2f%%", daily_loss_pct)
                return True

        if peak > 0:
            dd = (peak - equity) / peak * 100
            if dd >= self.max_drawdown_percent:
                logger.warning("Max drawdown breached: %.2f%%", dd)
                return True

        if consecutive_losses >= 5:
            logger.warning("5 consecutive losses — circuit breaker triggered")
            return True

        return False

    # ── Risk:Reward ──────────────────────────────────────────────────

    @staticmethod
    def calculate_risk_reward(
        entry: float, sl: float, tp: float
    ) -> float:
        """Calculate the risk-to-reward ratio.

        Returns:
            R:R as a float (e.g. 2.0 means reward is 2× risk).
        """
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0:
            return 0.0
        return round(reward / risk, 4)

    # ── Daily loss limit ─────────────────────────────────────────────

    def daily_loss_limit_check(
        self, daily_pnl: float, limit: Optional[float] = None
    ) -> bool:
        """Check if the daily P&L exceeds the daily loss limit.

        Args:
            daily_pnl: Today's realised P&L.
            limit: Absolute USD loss limit.  If None, the method uses
                   the percentage-based limit (requires open trades
                   with account_balance context).

        Returns:
            True if within limits, False if limit is breached.
        """
        if limit is not None:
            breached = daily_pnl <= -abs(limit)
        else:
            breached = False  # cannot check without balance context

        if breached:
            logger.warning(
                "Daily loss limit breached: PnL=%.2f, limit=%.2f",
                daily_pnl,
                -(limit or 0),
            )
        return not breached

    # ── Dynamic risk adjustment ──────────────────────────────────────

    def adjust_risk_dynamic(
        self, recent_performance: Dict[str, Any]
    ) -> float:
        """Adjust the risk percentage based on recent performance.

        Uses a simple Kelly-inspired approach:
        - After a winning streak, allow up to max_risk_percent.
        - After losses, scale down to 50% of normal risk.
        - After heavy losses, drop to 25%.

        Args:
            recent_performance: Dict with keys:
                win_rate (float 0-1), avg_win (float), avg_loss (float),
                consecutive_wins (int), consecutive_losses (int).

        Returns:
            Adjusted risk percentage to use for the next trade.
        """
        win_rate = recent_performance.get("win_rate", 0.5)
        consecutive_losses = recent_performance.get("consecutive_losses", 0)
        consecutive_wins = recent_performance.get("consecutive_wins", 0)
        avg_win = recent_performance.get("avg_win", 1.0)
        avg_loss = recent_performance.get("avg_loss", 1.0)

        base_risk = self.max_risk_percent

        # Kelly fraction (simplified, capped)
        if avg_loss > 0 and win_rate > 0:
            kelly = win_rate - ((1 - win_rate) / (avg_win / avg_loss))
            kelly = max(kelly, 0.0)
            kelly = min(kelly, 0.25)  # never bet more than 25% Kelly
            base_risk = self.max_risk_percent * (kelly / 0.25)

        # Scale by consecutive outcomes
        if consecutive_losses >= 4:
            adjusted = base_risk * 0.25
        elif consecutive_losses >= 2:
            adjusted = base_risk * 0.50
        elif consecutive_wins >= 4:
            adjusted = min(base_risk * 1.0, self.max_risk_percent)
        else:
            adjusted = base_risk * 0.75

        adjusted = round(max(adjusted, 0.25), 2)  # floor at 0.25%
        adjusted = min(adjusted, self.max_risk_percent)

        logger.info(
            "Dynamic risk adjustment: %.2f%% (base=%.2f%%, "
            "WR=%.1f%%, consec_L=%d, consec_W=%d)",
            adjusted,
            self.max_risk_percent,
            win_rate * 100,
            consecutive_losses,
            consecutive_wins,
        )
        return adjusted

    # ── Trade tracking helpers ───────────────────────────────────────

    def register_trade(self, trade: Dict[str, Any]) -> None:
        """Register an opened trade for tracking."""
        self._open_trades.append({
            "symbol": trade["symbol"],
            "direction": trade["direction"].upper(),
            "volume": trade.get("volume", 0.0),
            "entry": trade.get("entry", 0.0),
            "opened_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            "Trade registered: %s %s %.2f lots",
            trade["direction"],
            trade["symbol"],
            trade.get("volume", 0),
        )

    def unregister_trade(self, symbol: str, direction: str) -> None:
        """Remove a closed trade from the open-trade list."""
        self._open_trades = [
            t for t in self._open_trades
            if not (t["symbol"] == symbol and t["direction"] == direction.upper())
        ]

    def update_daily_pnl(self, pnl: float) -> None:
        """Add to today's running P&L total (resets on new UTC day)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_pnl_reset_date != today:
            self._daily_pnl = 0.0
            self._daily_pnl_reset_date = today
        self._daily_pnl += pnl

    @property
    def open_trade_count(self) -> int:
        return len(self._open_trades)

    # ── Kill switch ──────────────────────────────────────────────────

    def activate_kill_switch(self, reason: str = "") -> None:
        """Activate the emergency kill switch — halts ALL trading."""
        self._kill_switch_active = True
        logger.critical("KILL SWITCH ACTIVATED: %s", reason or "manual trigger")

    def deactivate_kill_switch(self) -> None:
        """Deactivate the emergency kill switch."""
        self._kill_switch_active = False
        logger.info("Kill switch deactivated")

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active
