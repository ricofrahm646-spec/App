"""
JARVIS Trading OS - Account Monitor
Background account surveillance: equity tracking, drawdown alerts, margin level
monitoring, emergency stop, and periodic snapshots for dashboards.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from mt5.connector.mt5_client import MT5Client, AccountInfo
from mt5.utils.helpers import format_currency, utc_now

logger = logging.getLogger("jarvis.mt5.account_monitor")

DEFAULT_POLL_INTERVAL_S = 2.0
DEFAULT_SNAPSHOT_INTERVAL_S = 60.0
DEFAULT_MAX_DRAWDOWN_PERCENT = 10.0
DEFAULT_CRITICAL_MARGIN_LEVEL = 120.0
MAX_SNAPSHOT_HISTORY = 1440  # 24 h of 1-minute snapshots


@dataclass
class AccountSnapshot:
    """Point-in-time snapshot of the account for dashboarding."""
    timestamp: datetime
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    drawdown_percent: float
    open_positions: int


@dataclass
class DrawdownState:
    """Running drawdown tracking."""
    peak_equity: float = 0.0
    current_equity: float = 0.0
    current_drawdown: float = 0.0
    current_drawdown_percent: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0


class AccountMonitor:
    """Continuously monitors the trading account in a background thread.

    Features:
        - Real-time equity tracking with high-water-mark drawdown.
        - Configurable drawdown threshold that triggers emergency close-all.
        - Margin-level alerts.
        - Periodic account snapshots stored in a ring buffer for dashboards.
        - Callback hooks for alerts and events.
    """

    def __init__(
        self,
        client: MT5Client,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        snapshot_interval: float = DEFAULT_SNAPSHOT_INTERVAL_S,
        max_drawdown_percent: float = DEFAULT_MAX_DRAWDOWN_PERCENT,
        critical_margin_level: float = DEFAULT_CRITICAL_MARGIN_LEVEL,
        on_drawdown_alert: Optional[Callable[[DrawdownState], None]] = None,
        on_margin_alert: Optional[Callable[[float], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None,
        on_snapshot: Optional[Callable[[AccountSnapshot], None]] = None,
    ) -> None:
        """Initialise the account monitor.

        Args:
            client: Connected ``MT5Client``.
            poll_interval: Seconds between equity polls.
            snapshot_interval: Seconds between dashboard snapshots.
            max_drawdown_percent: Drawdown threshold that triggers emergency stop.
            critical_margin_level: Margin level (%) that triggers an alert.
            on_drawdown_alert: Callback fired when drawdown exceeds 50 % of threshold.
            on_margin_alert: Callback fired when margin level drops below critical.
            on_emergency_stop: Callback fired on emergency close-all.
            on_snapshot: Callback fired each time a snapshot is taken.
        """
        self._client = client
        self._poll_interval = poll_interval
        self._snapshot_interval = snapshot_interval
        self._max_drawdown_percent = max_drawdown_percent
        self._critical_margin_level = critical_margin_level

        self._on_drawdown_alert = on_drawdown_alert
        self._on_margin_alert = on_margin_alert
        self._on_emergency_stop = on_emergency_stop
        self._on_snapshot = on_snapshot

        self._drawdown = DrawdownState()
        self._snapshots: deque[AccountSnapshot] = deque(maxlen=MAX_SNAPSHOT_HISTORY)
        self._active = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._emergency_triggered = False
        self._last_snapshot_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background monitoring thread."""
        if self._active:
            logger.warning("Account monitor already running")
            return
        self._active = True
        self._emergency_triggered = False
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="jarvis-account-monitor"
        )
        self._thread.start()
        logger.info(
            "Account monitor started (poll=%.1fs, snapshot=%.1fs, max_dd=%.1f%%)",
            self._poll_interval,
            self._snapshot_interval,
            self._max_drawdown_percent,
        )

    def stop(self) -> None:
        """Stop the monitoring thread gracefully."""
        self._active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._poll_interval * 3)
        logger.info("Account monitor stopped")

    @property
    def is_running(self) -> bool:
        """Return True if the monitor is actively polling."""
        return self._active

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_drawdown_state(self) -> DrawdownState:
        """Return a copy of the current drawdown state."""
        with self._lock:
            return DrawdownState(
                peak_equity=self._drawdown.peak_equity,
                current_equity=self._drawdown.current_equity,
                current_drawdown=self._drawdown.current_drawdown,
                current_drawdown_percent=self._drawdown.current_drawdown_percent,
                max_drawdown=self._drawdown.max_drawdown,
                max_drawdown_percent=self._drawdown.max_drawdown_percent,
            )

    def get_snapshots(self, last_n: int = 0) -> list[AccountSnapshot]:
        """Return recent account snapshots.

        Args:
            last_n: If > 0, return only the most recent *last_n* entries.

        Returns:
            List of ``AccountSnapshot`` instances (oldest first).
        """
        with self._lock:
            data = list(self._snapshots)
        if last_n > 0:
            return data[-last_n:]
        return data

    def get_latest_snapshot(self) -> Optional[AccountSnapshot]:
        """Return the most recent snapshot, or None."""
        with self._lock:
            if self._snapshots:
                return self._snapshots[-1]
        return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Background loop that polls account state."""
        while self._active:
            try:
                if not self._client.is_connected():
                    logger.warning("Account monitor: MT5 not connected, waiting…")
                    time.sleep(self._poll_interval * 2)
                    continue

                account = self._client.get_account_info()
                self._update_drawdown(account)
                self._check_margin(account)
                self._maybe_snapshot(account)

                if not self._emergency_triggered:
                    self._check_emergency(account)

            except Exception as exc:
                logger.error("Account monitor error: %s", exc)

            time.sleep(self._poll_interval)

    # ------------------------------------------------------------------
    # Drawdown tracking
    # ------------------------------------------------------------------

    def _update_drawdown(self, account: AccountInfo) -> None:
        """Update the high-water-mark drawdown calculation."""
        with self._lock:
            equity = account.equity
            self._drawdown.current_equity = equity

            if equity > self._drawdown.peak_equity:
                self._drawdown.peak_equity = equity

            if self._drawdown.peak_equity > 0:
                dd = self._drawdown.peak_equity - equity
                dd_pct = (dd / self._drawdown.peak_equity) * 100.0
            else:
                dd = 0.0
                dd_pct = 0.0

            self._drawdown.current_drawdown = dd
            self._drawdown.current_drawdown_percent = dd_pct

            if dd > self._drawdown.max_drawdown:
                self._drawdown.max_drawdown = dd
            if dd_pct > self._drawdown.max_drawdown_percent:
                self._drawdown.max_drawdown_percent = dd_pct

        warning_threshold = self._max_drawdown_percent * 0.5
        if dd_pct >= warning_threshold and self._on_drawdown_alert:
            try:
                self._on_drawdown_alert(self.get_drawdown_state())
            except Exception as exc:
                logger.error("Drawdown alert callback error: %s", exc)

    # ------------------------------------------------------------------
    # Margin monitoring
    # ------------------------------------------------------------------

    def _check_margin(self, account: AccountInfo) -> None:
        """Fire a margin alert if margin level is critically low."""
        ml = account.margin_level
        if ml > 0 and ml < self._critical_margin_level:
            logger.warning(
                "MARGIN ALERT: level %.1f%% < critical %.1f%%",
                ml,
                self._critical_margin_level,
            )
            if self._on_margin_alert:
                try:
                    self._on_margin_alert(ml)
                except Exception as exc:
                    logger.error("Margin alert callback error: %s", exc)

    # ------------------------------------------------------------------
    # Emergency stop
    # ------------------------------------------------------------------

    def _check_emergency(self, account: AccountInfo) -> None:
        """Trigger emergency close-all if drawdown exceeds the threshold."""
        with self._lock:
            dd_pct = self._drawdown.current_drawdown_percent

        if dd_pct >= self._max_drawdown_percent:
            self._emergency_triggered = True
            logger.critical(
                "EMERGENCY STOP: drawdown %.2f%% >= threshold %.2f%% — closing all positions",
                dd_pct,
                self._max_drawdown_percent,
            )
            try:
                results = self._client.close_all_orders()
                closed = sum(1 for r in results if r.success)
                logger.critical(
                    "Emergency close complete: %d/%d positions closed", closed, len(results)
                )
            except Exception as exc:
                logger.critical("Emergency close failed: %s", exc)

            if self._on_emergency_stop:
                try:
                    self._on_emergency_stop()
                except Exception as exc:
                    logger.error("Emergency stop callback error: %s", exc)

    def reset_emergency(self) -> None:
        """Reset the emergency flag so monitoring resumes normal operation.

        Call this after the operator has reviewed the emergency and wishes
        to allow new trades.
        """
        self._emergency_triggered = False
        with self._lock:
            self._drawdown.peak_equity = self._drawdown.current_equity
        logger.info("Emergency flag reset — monitoring resumed")

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def _maybe_snapshot(self, account: AccountInfo) -> None:
        """Take a periodic account snapshot for the dashboard."""
        now = time.monotonic()
        if now - self._last_snapshot_time < self._snapshot_interval:
            return
        self._last_snapshot_time = now

        positions = self._client.get_positions()

        with self._lock:
            dd_pct = self._drawdown.current_drawdown_percent

        snapshot = AccountSnapshot(
            timestamp=utc_now(),
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.free_margin,
            margin_level=account.margin_level,
            profit=account.profit,
            drawdown_percent=dd_pct,
            open_positions=len(positions),
        )

        with self._lock:
            self._snapshots.append(snapshot)

        logger.debug(
            "Snapshot: equity=%s dd=%.2f%% positions=%d",
            format_currency(account.equity),
            dd_pct,
            len(positions),
        )

        if self._on_snapshot:
            try:
                self._on_snapshot(snapshot)
            except Exception as exc:
                logger.error("Snapshot callback error: %s", exc)

    # ------------------------------------------------------------------
    # Convenience summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a JSON-friendly summary of the current account state."""
        dd = self.get_drawdown_state()
        snap = self.get_latest_snapshot()
        return {
            "monitoring": self._active,
            "emergency_triggered": self._emergency_triggered,
            "peak_equity": dd.peak_equity,
            "current_equity": dd.current_equity,
            "current_drawdown": dd.current_drawdown,
            "current_drawdown_percent": dd.current_drawdown_percent,
            "max_drawdown": dd.max_drawdown,
            "max_drawdown_percent": dd.max_drawdown_percent,
            "max_drawdown_threshold": self._max_drawdown_percent,
            "critical_margin_level": self._critical_margin_level,
            "snapshots_stored": len(self._snapshots),
            "latest_snapshot": {
                "timestamp": snap.timestamp.isoformat() if snap else None,
                "balance": snap.balance if snap else None,
                "equity": snap.equity if snap else None,
                "open_positions": snap.open_positions if snap else None,
            },
        }
