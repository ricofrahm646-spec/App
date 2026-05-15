"""
JARVIS Trade Logger.

Provides structured logging for all trade operations, performance events,
errors, and audit trails with automatic rotation and archival.
"""

import json
import logging
import logging.handlers
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_LOG_DIR = Path(os.environ.get("JARVIS_LOG_DIR", "logs"))
_TRADE_LOG = "trades.log"
_PERFORMANCE_LOG = "performance.log"
_ERROR_LOG = "errors.log"
_AUDIT_LOG = "audit.log"

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
_BACKUP_COUNT = 10             # keep 10 rotated files


# ── JSON formatter ───────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trade_data"):
            entry["trade_data"] = record.trade_data  # type: ignore[attr-defined]
        if hasattr(record, "performance_data"):
            entry["performance_data"] = record.performance_data  # type: ignore[attr-defined]
        if hasattr(record, "audit_data"):
            entry["audit_data"] = record.audit_data  # type: ignore[attr-defined]
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


# ── Setup helper ─────────────────────────────────────────────────────

def setup_logging(
    log_dir: Optional[str] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure root logging + JARVIS-specific rotating file handlers.

    Call once at application startup.

    Args:
        log_dir: Directory for log files (default: ``logs/``).
        console_level: Minimum level for console output.
        file_level: Minimum level for file output.
    """
    base = Path(log_dir) if log_dir else _LOG_DIR
    base.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(console_level)
        console.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(console)

    json_fmt = _JsonFormatter()

    for filename, level in [
        (_TRADE_LOG, file_level),
        (_PERFORMANCE_LOG, file_level),
        (_ERROR_LOG, logging.WARNING),
        (_AUDIT_LOG, file_level),
    ]:
        handler = logging.handlers.RotatingFileHandler(
            base / filename,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(json_fmt)
        root.addHandler(handler)

    logging.getLogger(__name__).info(
        "Logging initialised — dir=%s", base.resolve()
    )


# ── TradeLogger ──────────────────────────────────────────────────────

class TradeLogger:
    """Specialised logger for trade lifecycle events.

    Writes structured JSON lines to rotating log files and provides
    helper methods for common trade-related events.
    """

    def __init__(self, logger_name: str = "jarvis.trades") -> None:
        self._logger = logging.getLogger(logger_name)
        self._audit_logger = logging.getLogger("jarvis.audit")
        self._perf_logger = logging.getLogger("jarvis.performance")
        self._error_logger = logging.getLogger("jarvis.errors")

    # ── Trade lifecycle ──────────────────────────────────────────────

    def log_trade_opened(
        self,
        symbol: str,
        direction: str,
        volume: float,
        price: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        strategy: Optional[str] = None,
        ticket: Optional[int] = None,
        **extra: Any,
    ) -> None:
        """Log a trade open event."""
        data = {
            "event": "TRADE_OPENED",
            "ticket": ticket,
            "symbol": symbol,
            "direction": direction,
            "volume": volume,
            "price": price,
            "sl": sl,
            "tp": tp,
            "strategy": strategy,
            **extra,
        }
        record = self._logger.makeRecord(
            self._logger.name,
            logging.INFO,
            __file__,
            0,
            "Trade opened: %s %s %.2f lots @ %.5f",
            (direction, symbol, volume, price),
            None,
        )
        record.trade_data = data  # type: ignore[attr-defined]
        self._logger.handle(record)
        self._audit("TRADE_OPENED", data)

    def log_trade_closed(
        self,
        symbol: str,
        direction: str,
        volume: float,
        open_price: float,
        close_price: float,
        profit: float,
        pips: float,
        strategy: Optional[str] = None,
        ticket: Optional[int] = None,
        **extra: Any,
    ) -> None:
        """Log a trade close event."""
        data = {
            "event": "TRADE_CLOSED",
            "ticket": ticket,
            "symbol": symbol,
            "direction": direction,
            "volume": volume,
            "open_price": open_price,
            "close_price": close_price,
            "profit": profit,
            "pips": pips,
            "strategy": strategy,
            **extra,
        }
        lvl = logging.INFO if profit >= 0 else logging.WARNING
        record = self._logger.makeRecord(
            self._logger.name,
            lvl,
            __file__,
            0,
            "Trade closed: %s %s P&L=$%.2f (%+.1f pips)",
            (direction, symbol, profit, pips),
            None,
        )
        record.trade_data = data  # type: ignore[attr-defined]
        self._logger.handle(record)
        self._audit("TRADE_CLOSED", data)

    def log_trade_modified(
        self,
        symbol: str,
        ticket: Optional[int] = None,
        new_sl: Optional[float] = None,
        new_tp: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log a trade modification (SL/TP change)."""
        data = {
            "event": "TRADE_MODIFIED",
            "ticket": ticket,
            "symbol": symbol,
            "new_sl": new_sl,
            "new_tp": new_tp,
            **extra,
        }
        self._logger.info(
            "Trade modified: %s (ticket=%s) SL=%s TP=%s",
            symbol, ticket, new_sl, new_tp,
        )
        self._audit("TRADE_MODIFIED", data)

    # ── Signal events ────────────────────────────────────────────────

    def log_signal(
        self,
        signal_type: str,
        symbol: str,
        price: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        source: str = "ai",
        **extra: Any,
    ) -> None:
        """Log a generated trading signal."""
        data = {
            "event": "SIGNAL",
            "signal_type": signal_type,
            "symbol": symbol,
            "price": price,
            "sl": sl,
            "tp": tp,
            "source": source,
            **extra,
        }
        self._logger.info(
            "Signal: %s %s @ %.5f (source=%s)", signal_type, symbol, price, source
        )
        self._audit("SIGNAL", data)

    # ── Performance logging ──────────────────────────────────────────

    def log_performance(
        self,
        metrics: Dict[str, Any],
        period: str = "daily",
    ) -> None:
        """Log performance metrics snapshot.

        Args:
            metrics: Arbitrary metrics dict (balance, equity, win_rate, etc.)
            period: "daily", "weekly", "monthly", or "trade".
        """
        data = {"event": "PERFORMANCE", "period": period, **metrics}
        record = self._perf_logger.makeRecord(
            self._perf_logger.name,
            logging.INFO,
            __file__,
            0,
            "Performance [%s]: %s",
            (period, json.dumps(metrics, default=str)),
            None,
        )
        record.performance_data = data  # type: ignore[attr-defined]
        self._perf_logger.handle(record)

    def log_account_snapshot(
        self,
        balance: float,
        equity: float,
        margin: float = 0.0,
        free_margin: float = 0.0,
        drawdown: float = 0.0,
    ) -> None:
        """Log an account state snapshot."""
        self.log_performance(
            {
                "balance": balance,
                "equity": equity,
                "margin": margin,
                "free_margin": free_margin,
                "drawdown": drawdown,
            },
            period="snapshot",
        )

    # ── Error logging ────────────────────────────────────────────────

    def log_error(
        self,
        message: str,
        exc: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an error with optional exception and context.

        Captures the full stack trace when an exception is provided.
        """
        data: Dict[str, Any] = {
            "event": "ERROR",
            "message": message,
            "context": context or {},
        }
        if exc is not None:
            data["exception_type"] = type(exc).__name__
            data["exception_message"] = str(exc)
            data["traceback"] = traceback.format_exception(
                type(exc), exc, exc.__traceback__
            )
        self._error_logger.error(message, exc_info=exc is not None)
        self._audit("ERROR", data)

    def log_risk_event(
        self,
        event_type: str,
        details: Dict[str, Any],
    ) -> None:
        """Log a risk management event (warning, limit breach, kill switch)."""
        data = {"event": f"RISK_{event_type.upper()}", **details}
        self._logger.warning("Risk event [%s]: %s", event_type, details)
        self._audit(f"RISK_{event_type.upper()}", data)

    # ── Audit trail ──────────────────────────────────────────────────

    def _audit(self, action: str, data: Dict[str, Any]) -> None:
        """Write an immutable audit entry."""
        audit_entry = {
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        record = self._audit_logger.makeRecord(
            self._audit_logger.name,
            logging.INFO,
            __file__,
            0,
            "AUDIT: %s",
            (action,),
            None,
        )
        record.audit_data = audit_entry  # type: ignore[attr-defined]
        self._audit_logger.handle(record)

    # ── Bulk retrieval (from in-memory Python logging) ────────────────

    def get_recent_errors(self, count: int = 50) -> List[str]:
        """Return the last *count* ERROR-level messages from the error logger.

        Only works if a MemoryHandler or similar buffer is attached;
        otherwise returns an empty list.
        """
        for handler in self._error_logger.handlers:
            if isinstance(handler, logging.handlers.MemoryHandler):
                records = handler.buffer[-count:]
                return [handler.format(r) for r in records]
        return []
