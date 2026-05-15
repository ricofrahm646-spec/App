"""Centralized logging configuration for the JARVIS Trading OS.

Provides structured JSON logging with file rotation and per-module log levels.

Usage::

    from logging.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Trade executed", extra={"symbol": "EURUSD", "profit": 42.5})
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_DIR = Path(os.getenv("JARVIS_LOG_DIR", "logs"))
LOG_LEVEL = os.getenv("JARVIS_LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

MODULE_LOG_LEVELS: dict[str, int] = {
    "app.core": logging.DEBUG,
    "app.api": logging.INFO,
    "app.models": logging.INFO,
    "strategies": logging.DEBUG,
    "risk_management": logging.WARNING,
    "backtesting": logging.INFO,
    "mt5": logging.DEBUG,
    "telegram": logging.INFO,
    "tradingview": logging.INFO,
    "ai": logging.DEBUG,
    "uvicorn": logging.INFO,
    "sqlalchemy.engine": logging.WARNING,
}


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "symbol"):
            log_entry["symbol"] = record.symbol
        if hasattr(record, "profit"):
            log_entry["profit"] = record.profit
        if hasattr(record, "strategy"):
            log_entry["strategy"] = record.strategy
        if hasattr(record, "trade_id"):
            log_entry["trade_id"] = record.trade_id

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development use."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"{color}{record.levelname:<8}{self.RESET} "
            f"{timestamp} "
            f"[{record.name}] "
            f"{record.getMessage()}"
        )


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """Initialise the root logger with JSON file and console handlers.

    Call once at application startup (e.g. in ``app.main`` lifespan).
    """
    _ensure_log_dir()

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    if root.handlers:
        return

    file_handler = RotatingFileHandler(
        filename=LOG_DIR / "jarvis.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())

    error_handler = RotatingFileHandler(
        filename=LOG_DIR / "jarvis_error.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    console_handler.setFormatter(ConsoleFormatter())

    root.addHandler(file_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)

    for module, level in MODULE_LOG_LEVELS.items():
        logging.getLogger(module).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring the logging system is initialised.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.
    """
    if not logging.getLogger().handlers:
        setup_logging()
    return logging.getLogger(name)
