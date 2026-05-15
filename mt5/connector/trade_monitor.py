"""Background trade monitor with emergency stop, trailing stop, and drawdown alerts."""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from mt5.connector.mt5_client import MT5Client, TradeResult

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TradeSnapshot:
    ticket: int
    symbol: str
    order_type: int
    volume: float
    open_price: float
    current_price: float
    profit: float
    sl: float
    tp: float
    swap: float
    magic: int
    open_time: datetime
    comment: str = ""


@dataclass
class DrawdownState:
    peak_equity: float = 0.0
    current_equity: float = 0.0
    max_drawdown_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    alert_thresholds_hit: List[float] = field(default_factory=list)


@dataclass
class TrailingStopConfig:
    enabled: bool = True
    activation_pips: float = 20.0
    trail_distance_pips: float = 10.0
    step_pips: float = 1.0


@dataclass
class MonitorConfig:
    poll_interval: float = 5.0
    emergency_stop_loss_pct: float = 0.20
    drawdown_alert_thresholds: List[float] = field(default_factory=lambda: [0.05, 0.10, 0.15])
    trailing_stop: TrailingStopConfig = field(default_factory=TrailingStopConfig)
    max_daily_loss_pct: float = 0.05
    max_concurrent_trades: int = 1


NotifyCallback = Callable[[str, AlertLevel, Dict[str, Any]], Coroutine[Any, Any, None]]


class TradeMonitor:
    """Monitors open positions, enforces risk limits, and manages trailing stops."""

    def __init__(self, client: MT5Client, config: Optional[MonitorConfig] = None,
                 on_notify: Optional[NotifyCallback] = None):
        self._client = client
        self._config = config or MonitorConfig()
        self._on_notify = on_notify
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._drawdown = DrawdownState()
        self._known_tickets: Dict[int, TradeSnapshot] = {}
        self._daily_pnl: float = 0.0
        self._day_start: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def drawdown_state(self) -> DrawdownState:
        return self._drawdown

    async def start(self) -> None:
        """Start the background monitoring loop."""
        if self._running:
            logger.warning("Trade monitor already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Trade monitor started (poll every %.1fs)", self._config.poll_interval)

    async def stop(self) -> None:
        """Stop the background monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Trade monitor stopped")

    async def _notify(self, message: str, level: AlertLevel = AlertLevel.INFO,
                      data: Optional[Dict[str, Any]] = None) -> None:
        payload = data or {}
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        logger.log(
            {"info": logging.INFO, "warning": logging.WARNING, "critical": logging.CRITICAL}[level.value],
            "[TradeMonitor] %s | %s", level.value.upper(), message,
        )
        if self._on_notify:
            try:
                await self._on_notify(message, level, payload)
            except Exception as exc:
                logger.error("Notification callback failed: %s", exc)

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Monitor tick error: %s", exc, exc_info=True)
            await asyncio.sleep(self._config.poll_interval)

    async def _tick(self) -> None:
        if not self._client.is_connected:
            return

        account = await self._client.get_account_info()
        raw_positions = await self._client.get_open_positions()

        self._reset_daily_counter_if_needed()
        await self._update_drawdown(account.equity, account.balance)

        current_tickets: Dict[int, TradeSnapshot] = {}
        for pos in raw_positions:
            snap = _position_to_snapshot(pos)
            current_tickets[snap.ticket] = snap

        opened = set(current_tickets) - set(self._known_tickets)
        closed = set(self._known_tickets) - set(current_tickets)

        for ticket in opened:
            snap = current_tickets[ticket]
            await self._notify(
                f"Trade opened: {snap.symbol} {'BUY' if snap.order_type == 0 else 'SELL'} "
                f"{snap.volume} @ {snap.open_price}",
                AlertLevel.INFO,
                {"event": "trade_opened", "ticket": ticket, "snapshot": _snap_dict(snap)},
            )

        for ticket in closed:
            old = self._known_tickets[ticket]
            self._daily_pnl += old.profit
            await self._notify(
                f"Trade closed: {old.symbol} ticket={ticket} profit={old.profit:.2f}",
                AlertLevel.INFO,
                {"event": "trade_closed", "ticket": ticket, "last_profit": old.profit},
            )

        for ticket, snap in current_tickets.items():
            await self._check_emergency_stop(snap, account.balance)
            await self._apply_trailing_stop(snap)

        await self._check_daily_loss_limit(account.balance)

        self._known_tickets = current_tickets

    def _reset_daily_counter_if_needed(self) -> None:
        now = datetime.now(timezone.utc)
        if self._day_start is None or now.date() != self._day_start.date():
            self._day_start = now
            self._daily_pnl = 0.0

    async def _update_drawdown(self, equity: float, balance: float) -> None:
        if equity <= 0:
            return
        if equity > self._drawdown.peak_equity:
            self._drawdown.peak_equity = equity
        self._drawdown.current_equity = equity

        dd_pct = (self._drawdown.peak_equity - equity) / self._drawdown.peak_equity
        self._drawdown.current_drawdown_pct = dd_pct
        if dd_pct > self._drawdown.max_drawdown_pct:
            self._drawdown.max_drawdown_pct = dd_pct

        for threshold in self._config.drawdown_alert_thresholds:
            if dd_pct >= threshold and threshold not in self._drawdown.alert_thresholds_hit:
                self._drawdown.alert_thresholds_hit.append(threshold)
                await self._notify(
                    f"Drawdown alert: {dd_pct:.1%} (threshold {threshold:.0%})",
                    AlertLevel.WARNING if threshold < 0.15 else AlertLevel.CRITICAL,
                    {"event": "drawdown_alert", "drawdown_pct": dd_pct, "threshold": threshold},
                )

    async def _check_emergency_stop(self, snap: TradeSnapshot, balance: float) -> None:
        """Close trade if unrealised loss exceeds emergency threshold (default 20%)."""
        if balance <= 0 or snap.profit >= 0:
            return
        loss_pct = abs(snap.profit) / balance
        if loss_pct >= self._config.emergency_stop_loss_pct:
            await self._notify(
                f"EMERGENCY STOP: ticket={snap.ticket} {snap.symbol} loss={snap.profit:.2f} "
                f"({loss_pct:.1%} of balance)",
                AlertLevel.CRITICAL,
                {"event": "emergency_stop", "ticket": snap.ticket, "loss_pct": loss_pct},
            )
            result = await self._client.close_trade(snap.ticket)
            if result.success:
                await self._notify(
                    f"Emergency close successful: ticket={snap.ticket}",
                    AlertLevel.CRITICAL,
                    {"event": "emergency_close_ok", "ticket": snap.ticket},
                )
            else:
                await self._notify(
                    f"Emergency close FAILED: ticket={snap.ticket} error={result.error}",
                    AlertLevel.CRITICAL,
                    {"event": "emergency_close_fail", "ticket": snap.ticket, "error": result.error},
                )

    async def _apply_trailing_stop(self, snap: TradeSnapshot) -> None:
        """Move SL in the direction of profit once activation threshold is reached."""
        ts_cfg = self._config.trailing_stop
        if not ts_cfg.enabled:
            return

        sym_info = await self._client.get_symbol_info(snap.symbol)
        if not sym_info or sym_info.point <= 0:
            return

        point = sym_info.point
        activation = ts_cfg.activation_pips * point
        trail = ts_cfg.trail_distance_pips * point
        step = ts_cfg.step_pips * point

        if snap.order_type == 0:  # BUY
            profit_distance = snap.current_price - snap.open_price
            if profit_distance < activation:
                return
            new_sl = snap.current_price - trail
            new_sl = _round_price(new_sl, sym_info.digits)
            if new_sl <= snap.sl:
                return
            if snap.sl > 0 and (new_sl - snap.sl) < step:
                return
        else:  # SELL
            profit_distance = snap.open_price - snap.current_price
            if profit_distance < activation:
                return
            new_sl = snap.current_price + trail
            new_sl = _round_price(new_sl, sym_info.digits)
            if snap.sl > 0 and new_sl >= snap.sl:
                return
            if snap.sl > 0 and (snap.sl - new_sl) < step:
                return

        result = await self._client.modify_trade(snap.ticket, sl=new_sl)
        if result.success:
            logger.info("Trailing stop updated: ticket=%d new_sl=%.5f", snap.ticket, new_sl)
        else:
            logger.warning("Trailing stop update failed: ticket=%d error=%s", snap.ticket, result.error)

    async def _check_daily_loss_limit(self, balance: float) -> None:
        if balance <= 0:
            return
        daily_loss_pct = abs(min(self._daily_pnl, 0)) / balance
        if daily_loss_pct >= self._config.max_daily_loss_pct:
            positions = await self._client.get_open_positions()
            if positions:
                await self._notify(
                    f"Daily loss limit hit ({daily_loss_pct:.1%}). Closing all positions.",
                    AlertLevel.CRITICAL,
                    {"event": "daily_loss_limit", "daily_pnl": self._daily_pnl, "pct": daily_loss_pct},
                )
                for pos in positions:
                    ticket = pos.get("ticket")
                    if ticket:
                        await self._client.close_trade(int(ticket))


def _position_to_snapshot(pos: Dict[str, Any]) -> TradeSnapshot:
    open_time_raw = pos.get("time", 0)
    if isinstance(open_time_raw, (int, float)):
        open_time = datetime.fromtimestamp(open_time_raw, tz=timezone.utc)
    else:
        open_time = open_time_raw

    return TradeSnapshot(
        ticket=int(pos.get("ticket", 0)),
        symbol=str(pos.get("symbol", "")),
        order_type=int(pos.get("type", 0)),
        volume=float(pos.get("volume", 0)),
        open_price=float(pos.get("price_open", 0)),
        current_price=float(pos.get("price_current", 0)),
        profit=float(pos.get("profit", 0)),
        sl=float(pos.get("sl", 0)),
        tp=float(pos.get("tp", 0)),
        swap=float(pos.get("swap", 0)),
        magic=int(pos.get("magic", 0)),
        open_time=open_time,
        comment=str(pos.get("comment", "")),
    )


def _snap_dict(snap: TradeSnapshot) -> Dict[str, Any]:
    return {
        "ticket": snap.ticket, "symbol": snap.symbol,
        "type": snap.order_type, "volume": snap.volume,
        "open_price": snap.open_price, "current_price": snap.current_price,
        "profit": snap.profit, "sl": snap.sl, "tp": snap.tp,
    }


def _round_price(price: float, digits: int) -> float:
    return round(price, digits)
