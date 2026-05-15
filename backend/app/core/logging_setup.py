"""Centralised loguru configuration. Imported once at app startup."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from backend.app.core.config import settings


_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )
    logger.add(
        log_dir / "jarvis.log",
        level=settings.log_level,
        rotation="20 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
    )
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        rotation="20 MB",
        retention="60 days",
        enqueue=True,
    )

    _CONFIGURED = True
    logger.info("Logging configured (level={})", settings.log_level)


__all__ = ["setup_logging", "logger"]
