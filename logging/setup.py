"""
JARVIS Logging Setup
Configures structured logging with Loguru for all JARVIS modules.
"""

import sys
import os
from pathlib import Path
from loguru import logger


LOG_DIR = Path(os.getenv("LOG_DIR", "/workspace/logging/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configure JARVIS logging with file rotation and JSON output."""
    logger.remove()

    # Console output (colored)
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )

    # Plain text log (rotating)
    logger.add(
        LOG_DIR / "jarvis.log",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="50 MB",
        retention="30 days",
        compression="zip",
    )

    # JSON structured log
    logger.add(
        LOG_DIR / "jarvis.json.log",
        level=level,
        format="{message}",
        serialize=True,
        rotation="100 MB",
        retention="90 days",
        compression="gz",
    )

    # Error-only log
    logger.add(
        LOG_DIR / "jarvis.errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}\n{exception}",
        rotation="20 MB",
        retention="60 days",
        backtrace=True,
        diagnose=True,
    )

    # Trading-specific log
    logger.add(
        LOG_DIR / "trading.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        filter=lambda record: "trading" in record["name"].lower() or "mt5" in record["name"].lower(),
        rotation="20 MB",
        retention="90 days",
    )

    logger.info("JARVIS logging initialized (level={})", level)


# Call on import
setup_logging()
