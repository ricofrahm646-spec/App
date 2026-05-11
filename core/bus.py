"""
core.bus
========
Lightweight, thread-safe, file-backed event bus used by all agents.

Every component (trader, vision, ghost, brain, dashboard) writes structured
events here. The Streamlit dashboard reads the same files to render in real
time. This makes the agents loosely coupled and crash-resilient.

Files written (under logs/ by default):
  * events.log     - JSON-lines stream of every event
  * trades.log     - JSON-lines stream of trades
  * signals.csv    - one signal per line for chart plotting
  * equity.csv     - timestamp,balance,equity for chart plotting
"""
from __future__ import annotations

import csv
import json
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Optional

from config import BRAIN, LOGS_DIR

_LOCK = threading.RLock()
_IN_MEMORY_EVENTS: Deque[Dict[str, Any]] = deque(maxlen=2000)


def _now() -> float:
    return time.time()


def _iso(ts: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts or _now()))


@dataclass
class Event:
    source: str
    level: str = "INFO"             # INFO | WARN | ERROR | TRADE | SIGNAL | VISION
    message: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ts_iso"] = _iso(self.ts)
        return d


def publish(event: Event) -> None:
    """Append the event to the in-memory ring + events.log."""
    with _LOCK:
        _IN_MEMORY_EVENTS.append(event.to_dict())
        try:
            BRAIN.event_log.parent.mkdir(parents=True, exist_ok=True)
            with BRAIN.event_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except OSError:
            pass


def log(source: str, message: str, level: str = "INFO", **payload: Any) -> None:
    publish(Event(source=source, level=level, message=message, payload=payload))


def log_trade(payload: Dict[str, Any]) -> None:
    publish(Event(source="trader", level="TRADE", message=payload.get("action", "trade"), payload=payload))
    try:
        with BRAIN.trade_log.open("a", encoding="utf-8") as f:
            payload = {"ts_iso": _iso(), **payload}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_signal(symbol: str, direction: str, confluence: float, **extras: Any) -> None:
    publish(Event(
        source="trader",
        level="SIGNAL",
        message=f"{direction} {symbol} ({confluence:.0%})",
        payload={"symbol": symbol, "direction": direction, "confluence": confluence, **extras},
    ))
    try:
        new_file = not BRAIN.signals_log.exists()
        with BRAIN.signals_log.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["ts_iso", "symbol", "direction", "confluence", "price", "sl", "tp"])
            w.writerow([
                _iso(),
                symbol,
                direction,
                f"{confluence:.4f}",
                extras.get("price", ""),
                extras.get("sl", ""),
                extras.get("tp", ""),
            ])
    except OSError:
        pass


def log_equity(balance: float, equity: float) -> None:
    try:
        new_file = not BRAIN.equity_log.exists()
        with BRAIN.equity_log.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["ts_iso", "balance", "equity"])
            w.writerow([_iso(), f"{balance:.2f}", f"{equity:.2f}"])
    except OSError:
        pass


def recent_events(n: int = 200) -> Iterable[Dict[str, Any]]:
    with _LOCK:
        return list(_IN_MEMORY_EVENTS)[-n:]


def tail_events(n: int = 200, log_path: Optional[Path] = None) -> Iterable[Dict[str, Any]]:
    """Tail the events.log file (used by the dashboard which may live in a
    different process)."""
    p = log_path or BRAIN.event_log
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-n:]
        out = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except OSError:
        return []


__all__ = [
    "Event",
    "publish",
    "log",
    "log_trade",
    "log_signal",
    "log_equity",
    "recent_events",
    "tail_events",
]
