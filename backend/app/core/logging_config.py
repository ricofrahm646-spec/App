from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # ── Shared processors ────────────────────────────────────────────────
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_json_format:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # ── Console handler ──────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # ── Rotating file handler – general log ──────────────────────────────
    app_file_handler = RotatingFileHandler(
        filename=log_dir / "jarvis.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    app_file_handler.setFormatter(formatter)

    # ── Rotating file handler – errors only ──────────────────────────────
    error_file_handler = RotatingFileHandler(
        filename=log_dir / "jarvis_errors.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    # ── Rotating file handler – trades ───────────────────────────────────
    trade_file_handler = RotatingFileHandler(
        filename=log_dir / "trades.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    trade_file_handler.setFormatter(formatter)

    # ── Root logger ──────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(settings.log_level.value)
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(app_file_handler)
    root.addHandler(error_file_handler)

    # ── Trade-specific logger ────────────────────────────────────────────
    trade_logger = logging.getLogger("jarvis.trades")
    trade_logger.addHandler(trade_file_handler)
    trade_logger.propagate = True

    # Quieten noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str = "jarvis") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
