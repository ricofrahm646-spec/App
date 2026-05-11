"""Safety primitives for emergency stopping automated operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class KillSwitchState:
    """Current status of automation kill switch."""

    active: bool
    reason: str
    changed_at: str


class KillSwitch:
    """Thread-safe kill switch for globally stopping automation."""

    def __init__(self) -> None:
        self._active = False
        self._reason = "initialized"
        self._changed_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self._lock = asyncio.Lock()

    async def activate(self, reason: str = "manual_abort") -> KillSwitchState:
        async with self._lock:
            self._active = True
            self._reason = reason
            self._changed_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            return self.state

    async def reset(self, reason: str = "manual_reset") -> KillSwitchState:
        async with self._lock:
            self._active = False
            self._reason = reason
            self._changed_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            return self.state

    async def is_active(self) -> bool:
        async with self._lock:
            return self._active

    @property
    def state(self) -> KillSwitchState:
        return KillSwitchState(
            active=self._active,
            reason=self._reason,
            changed_at=self._changed_at,
        )

