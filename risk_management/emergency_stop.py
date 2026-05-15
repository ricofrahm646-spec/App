"""
JARVIS AI Trading OS - Emergency Stop System

Continuously monitors all open positions and account metrics, triggers
emergency closure when risk thresholds are breached, and locks trading
for a configurable cooldown period.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types & data classes
# ---------------------------------------------------------------------------

class EmergencyReason(Enum):
    MAX_DRAWDOWN = auto()
    DAILY_LOSS = auto()
    SINGLE_TRADE_LOSS = auto()
    CONNECTION_LOST = auto()
    MANUAL = auto()
    CONSECUTIVE_LOSSES = auto()


@dataclass
class EmergencyEvent:
    reason: EmergencyReason
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    positions_closed: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergencyConfig:
    max_drawdown_pct: float = 0.20
    max_daily_loss_pct: float = 0.05
    single_trade_max_loss_pct: float = 0.20
    max_consecutive_losses: int = 10
    cooldown_seconds: int = 3600
    monitor_interval_seconds: float = 1.0
    connection_timeout_seconds: float = 10.0


NotifyCallback = Callable[[EmergencyEvent], None]
AsyncNotifyCallback = Callable[[EmergencyEvent], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Account / Position protocols
# ---------------------------------------------------------------------------

@dataclass
class PositionSnapshot:
    ticket: str
    symbol: str
    direction: str
    volume: float
    entry_price: float
    current_price: float
    unrealized_pnl: float


@dataclass
class AccountSnapshot:
    balance: float
    equity: float
    margin: float
    free_margin: float
    daily_pnl: float
    open_positions: list[PositionSnapshot] = field(default_factory=list)
    connected: bool = True


class BrokerBridge:
    """
    Abstract interface to the broker connection.

    Concrete implementations wrap MT5, CCXT, or other APIs.
    """

    def get_account_snapshot(self) -> AccountSnapshot:
        raise NotImplementedError

    def close_position(self, ticket: str) -> bool:
        raise NotImplementedError

    def close_all_positions(self) -> list[str]:
        raise NotImplementedError

    def is_connected(self) -> bool:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Emergency Stop
# ---------------------------------------------------------------------------

class EmergencyStop:
    """
    Monitors account and position risk in real-time and triggers emergency
    actions when thresholds are breached.

    Supports both synchronous polling (``run_check``) and an ``asyncio``
    monitoring loop (``start_monitoring``/``stop_monitoring``).
    """

    def __init__(
        self,
        config: Optional[EmergencyConfig] = None,
        broker: Optional[BrokerBridge] = None,
        on_emergency: Optional[NotifyCallback] = None,
        on_emergency_async: Optional[AsyncNotifyCallback] = None,
    ) -> None:
        self.config = config or EmergencyConfig()
        self._broker = broker
        self._on_emergency = on_emergency
        self._on_emergency_async = on_emergency_async

        self._active = False
        self._locked_until: Optional[datetime] = None
        self._equity_peak: float = 0.0
        self._event_log: list[EmergencyEvent] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    # ----- public API -----

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_locked(self) -> bool:
        if self._active:
            return True
        if self._locked_until and datetime.utcnow() < self._locked_until:
            return True
        return False

    @property
    def event_log(self) -> list[EmergencyEvent]:
        return list(self._event_log)

    @property
    def lock_remaining_seconds(self) -> float:
        if not self._locked_until:
            return 0.0
        remaining = (self._locked_until - datetime.utcnow()).total_seconds()
        return max(0.0, remaining)

    def run_check(self, snapshot: Optional[AccountSnapshot] = None) -> Optional[EmergencyEvent]:
        if snapshot is None:
            if self._broker is None:
                return None
            try:
                snapshot = self._broker.get_account_snapshot()
            except Exception:
                logger.exception("Failed to get account snapshot")
                return self._trigger(EmergencyReason.CONNECTION_LOST, "Cannot retrieve account data")

        if self._equity_peak == 0.0:
            self._equity_peak = snapshot.equity
        if snapshot.equity > self._equity_peak:
            self._equity_peak = snapshot.equity

        if not snapshot.connected:
            return self._trigger(EmergencyReason.CONNECTION_LOST, "Connection to broker lost")

        drawdown = self._current_drawdown(snapshot.equity)
        if drawdown >= self.config.max_drawdown_pct:
            return self._trigger(
                EmergencyReason.MAX_DRAWDOWN,
                f"Account drawdown {drawdown*100:.1f}% exceeds {self.config.max_drawdown_pct*100:.0f}%",
                details={"drawdown_pct": drawdown},
            )

        if snapshot.balance > 0:
            daily_loss_pct = abs(snapshot.daily_pnl) / snapshot.balance if snapshot.daily_pnl < 0 else 0.0
            if daily_loss_pct >= self.config.max_daily_loss_pct:
                return self._trigger(
                    EmergencyReason.DAILY_LOSS,
                    f"Daily loss {daily_loss_pct*100:.1f}% exceeds {self.config.max_daily_loss_pct*100:.0f}%",
                    details={"daily_loss_pct": daily_loss_pct},
                )

        for pos in snapshot.open_positions:
            if pos.entry_price <= 0:
                continue
            position_value = pos.entry_price * pos.volume
            if position_value <= 0:
                continue
            loss_ratio = abs(pos.unrealized_pnl) / position_value if pos.unrealized_pnl < 0 else 0.0
            if loss_ratio >= self.config.single_trade_max_loss_pct:
                return self._trigger(
                    EmergencyReason.SINGLE_TRADE_LOSS,
                    f"Position {pos.ticket} ({pos.symbol}) loss {loss_ratio*100:.1f}% exceeds threshold",
                    details={"ticket": pos.ticket, "loss_pct": loss_ratio},
                )

        return None

    def trigger_manual(self, reason: str = "Manual emergency stop") -> EmergencyEvent:
        return self._trigger(EmergencyReason.MANUAL, reason)

    def reset(self) -> None:
        self._active = False
        self._locked_until = None
        logger.info("Emergency stop reset")

    def unlock(self) -> None:
        self._active = False
        self._locked_until = None
        logger.info("Emergency stop unlocked")

    # ----- async monitoring loop -----

    async def start_monitoring(self) -> None:
        if self._monitoring:
            logger.warning("Monitoring already active")
            return
        self._monitoring = True
        self._monitor_task = asyncio.ensure_future(self._monitor_loop())
        logger.info("Emergency stop monitoring started (interval=%.1fs)", self.config.monitor_interval_seconds)

    async def stop_monitoring(self) -> None:
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("Emergency stop monitoring stopped")

    async def _monitor_loop(self) -> None:
        while self._monitoring:
            try:
                event = self.run_check()
                if event and self._on_emergency_async:
                    await self._on_emergency_async(event)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in emergency monitor loop")
            await asyncio.sleep(self.config.monitor_interval_seconds)

    # ----- internals -----

    def _current_drawdown(self, equity: float) -> float:
        if self._equity_peak <= 0:
            return 0.0
        return max(0.0, (self._equity_peak - equity) / self._equity_peak)

    def _trigger(
        self,
        reason: EmergencyReason,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> EmergencyEvent:
        logger.critical("EMERGENCY STOP [%s]: %s", reason.name, message)

        positions_closed = 0
        if self._broker:
            try:
                closed = self._broker.close_all_positions()
                positions_closed = len(closed)
                logger.warning("Closed %d positions", positions_closed)
            except Exception:
                logger.exception("Failed to close positions during emergency")

        self._active = True
        self._locked_until = datetime.utcnow() + timedelta(seconds=self.config.cooldown_seconds)

        event = EmergencyEvent(
            reason=reason,
            message=message,
            positions_closed=positions_closed,
            details=details or {},
        )
        self._event_log.append(event)

        if self._on_emergency:
            try:
                self._on_emergency(event)
            except Exception:
                logger.exception("Emergency callback failed")

        return event
