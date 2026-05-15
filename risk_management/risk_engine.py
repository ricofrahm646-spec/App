"""
JARVIS AI Trading OS - Risk Management Engine

Enforces position-sizing rules, daily-loss limits, drawdown caps,
and emergency-stop triggers for every trade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, auto
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RiskMetrics:
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    risk_reward_ratio: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    consecutive_losses: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str
    adjusted_volume: float = 0.0


@dataclass
class TradeResult:
    symbol: str
    direction: str
    volume: float
    entry_price: float
    exit_price: float
    pnl: float
    commission: float = 0.0
    swap: float = 0.0
    closed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OpenPosition:
    ticket: str
    symbol: str
    direction: str
    volume: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    opened_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class RiskConfig:
    max_risk_per_trade: float = 0.02
    max_daily_loss_pct: float = 0.05
    max_drawdown_pct: float = 0.20
    single_trade_max_loss_pct: float = 0.20
    max_concurrent_trades: int = 1
    allow_hedging: bool = False
    max_consecutive_losses: int = 10
    cooldown_after_emergency_seconds: int = 3600
    account_balance: float = 10_000.0
    account_currency: str = "USD"


# ---------------------------------------------------------------------------
# Risk Engine
# ---------------------------------------------------------------------------

class RiskEngine:
    """
    Central risk-management component.

    Rules enforced:
    - Max 1 concurrent trade (configurable)
    - No simultaneous buy and sell on the same symbol (unless hedging enabled)
    - Max 2 % risk per trade (configurable)
    - Max 5 % daily loss
    - Close trade at 20 % loss
    - Emergency stop system integration
    """

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        on_emergency: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config or RiskConfig()
        self._on_emergency = on_emergency

        self._balance = self.config.account_balance
        self._equity_peak = self._balance
        self._daily_pnl = 0.0
        self._daily_date: date = date.today()
        self._open_positions: dict[str, OpenPosition] = {}
        self._trade_history: list[TradeResult] = []
        self._consecutive_losses = 0
        self._locked_until: Optional[datetime] = None
        self._emergency_active = False

    # ----- public API -----

    def check_trade_allowed(
        self,
        symbol: str,
        direction: str,
        volume: float,
    ) -> RiskCheckResult:
        self._rotate_daily()

        if self._emergency_active:
            return RiskCheckResult(False, "Emergency stop active — trading locked", 0.0)

        if self._locked_until and datetime.utcnow() < self._locked_until:
            remaining = (self._locked_until - datetime.utcnow()).seconds
            return RiskCheckResult(False, f"Trading locked for {remaining}s after emergency stop", 0.0)

        if len(self._open_positions) >= self.config.max_concurrent_trades:
            return RiskCheckResult(False, f"Max concurrent trades ({self.config.max_concurrent_trades}) reached", 0.0)

        if not self.config.allow_hedging:
            for pos in self._open_positions.values():
                if pos.symbol == symbol and pos.direction != direction.upper():
                    return RiskCheckResult(False, f"Hedging not allowed: existing {pos.direction} on {symbol}", 0.0)

        if self.check_daily_loss_limit():
            return RiskCheckResult(False, "Daily loss limit reached", 0.0)

        if self.check_max_drawdown():
            self._trigger_emergency("Max drawdown exceeded")
            return RiskCheckResult(False, "Max drawdown exceeded — emergency stop triggered", 0.0)

        adjusted = self._clamp_volume(volume)
        return RiskCheckResult(True, "Trade allowed", adjusted)

    def calculate_position_size(
        self,
        symbol: str,
        sl_distance: float,
        risk_pct: Optional[float] = None,
    ) -> float:
        risk = risk_pct if risk_pct is not None else self.config.max_risk_per_trade
        risk_amount = self._balance * risk
        if sl_distance <= 0:
            return 0.0
        raw_lots = risk_amount / sl_distance
        return round(max(0.01, min(raw_lots, 10.0)), 2)

    def check_daily_loss_limit(self) -> bool:
        self._rotate_daily()
        limit = self._balance * self.config.max_daily_loss_pct
        return self._daily_pnl <= -limit

    def check_max_drawdown(self) -> bool:
        if self._equity_peak == 0:
            return False
        current_dd = (self._equity_peak - self._balance) / self._equity_peak
        return current_dd >= self.config.max_drawdown_pct

    def get_risk_metrics(self) -> RiskMetrics:
        self._rotate_daily()
        total = len(self._trade_history)
        wins = [t for t in self._trade_history if t.pnl > 0]
        losses = [t for t in self._trade_history if t.pnl <= 0]
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))

        dd = (self._equity_peak - self._balance) / self._equity_peak if self._equity_peak else 0.0

        pnl_list = [t.pnl for t in self._trade_history]
        sharpe = 0.0
        if len(pnl_list) >= 2:
            import numpy as np
            arr = np.array(pnl_list)
            std = arr.std()
            if std > 0:
                sharpe = float(arr.mean() / std * (252 ** 0.5))

        avg_win = (gross_profit / len(wins)) if wins else 0.0
        avg_loss = (gross_loss / len(losses)) if losses else 0.0
        rr = avg_win / avg_loss if avg_loss > 0 else 0.0

        return RiskMetrics(
            daily_pnl=round(self._daily_pnl, 2),
            max_drawdown=round(dd * 100, 2),
            current_drawdown=round(dd * 100, 2),
            win_rate=round(len(wins) / total * 100, 2) if total else 0.0,
            profit_factor=round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
            sharpe_ratio=round(sharpe, 2),
            risk_reward_ratio=round(rr, 2),
            total_trades=total,
            winning_trades=len(wins),
            losing_trades=len(losses),
            consecutive_losses=self._consecutive_losses,
            largest_win=round(max((t.pnl for t in wins), default=0.0), 2),
            largest_loss=round(min((t.pnl for t in losses), default=0.0), 2),
        )

    def emergency_close_all(self) -> list[str]:
        closed: list[str] = []
        for ticket, pos in list(self._open_positions.items()):
            logger.warning("EMERGENCY CLOSE: %s %s %s @ %.5f",
                           pos.direction, pos.volume, pos.symbol, pos.current_price)
            closed.append(ticket)
        self._open_positions.clear()
        self._emergency_active = True
        from datetime import timedelta
        self._locked_until = datetime.utcnow() + timedelta(seconds=self.config.cooldown_after_emergency_seconds)
        return closed

    def update_after_trade(self, trade_result: TradeResult) -> None:
        self._rotate_daily()
        self._balance += trade_result.pnl
        self._daily_pnl += trade_result.pnl
        self._trade_history.append(trade_result)

        if self._balance > self._equity_peak:
            self._equity_peak = self._balance

        if trade_result.pnl <= 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        if self._consecutive_losses >= self.config.max_consecutive_losses:
            self._trigger_emergency(
                f"Max consecutive losses ({self.config.max_consecutive_losses}) reached"
            )

        loss_pct = abs(trade_result.pnl) / self._balance if self._balance > 0 else 0
        if trade_result.pnl < 0 and loss_pct >= self.config.single_trade_max_loss_pct:
            logger.warning("Single trade loss %.1f%% exceeds threshold", loss_pct * 100)

        if self.check_daily_loss_limit():
            self._trigger_emergency("Daily loss limit exceeded after trade close")

    def register_position(self, position: OpenPosition) -> None:
        self._open_positions[position.ticket] = position

    def unregister_position(self, ticket: str) -> Optional[OpenPosition]:
        return self._open_positions.pop(ticket, None)

    def update_position_price(self, ticket: str, current_price: float) -> None:
        pos = self._open_positions.get(ticket)
        if not pos:
            return
        pos.current_price = current_price
        if pos.direction == "BUY":
            pos.unrealized_pnl = (current_price - pos.entry_price) * pos.volume
        else:
            pos.unrealized_pnl = (pos.entry_price - current_price) * pos.volume

        if pos.entry_price > 0:
            loss_ratio = abs(pos.unrealized_pnl) / (pos.entry_price * pos.volume) if pos.volume else 0
            if pos.unrealized_pnl < 0 and loss_ratio >= self.config.single_trade_max_loss_pct:
                self._trigger_emergency(f"Position {ticket} exceeds {self.config.single_trade_max_loss_pct*100:.0f}% loss")

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def open_positions(self) -> dict[str, OpenPosition]:
        return dict(self._open_positions)

    @property
    def is_locked(self) -> bool:
        if self._emergency_active:
            return True
        if self._locked_until and datetime.utcnow() < self._locked_until:
            return True
        return False

    def unlock(self) -> None:
        self._emergency_active = False
        self._locked_until = None
        logger.info("Risk engine unlocked manually")

    # ----- internals -----

    def _rotate_daily(self) -> None:
        today = date.today()
        if today != self._daily_date:
            self._daily_pnl = 0.0
            self._daily_date = today

    def _clamp_volume(self, volume: float) -> float:
        risk_amount = self._balance * self.config.max_risk_per_trade
        max_volume = min(volume, risk_amount / max(self._balance * 0.01, 1.0))
        return round(max(0.01, max_volume), 2)

    def _trigger_emergency(self, reason: str) -> None:
        logger.critical("EMERGENCY STOP: %s", reason)
        if self._on_emergency:
            self._on_emergency(reason)
        self.emergency_close_all()
