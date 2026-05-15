import sys
import json as _json
from pathlib import Path
from typing import Any

from loguru import logger as _logger

from app.config import settings


# ── Log directory ──────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── Custom JSON formatter ─────────────────────────────────────────────────────

def _json_formatter(record: dict) -> str:  # type: ignore[type-arg]
    """Serialise a Loguru record to a single-line JSON string."""
    log_entry: dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    if record["exception"]:
        exc = record["exception"]
        log_entry["exception"] = {
            "type": exc.type.__name__ if exc.type else None,
            "value": str(exc.value) if exc.value else None,
        }
    if record.get("extra"):
        log_entry["extra"] = record["extra"]
    return _json.dumps(log_entry, default=str) + "\n"


def _sink_json(message: "loguru.Message") -> None:  # type: ignore[name-defined]  # noqa: F821
    """Loguru sink that writes JSON-formatted records to the rotating log file."""
    _json_file_handler.write(_json_formatter(message.record))
    _json_file_handler.flush()


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Configure all Loguru sinks.

    Sinks:
    - stderr  : human-readable coloured output (development)
    - app.log : plain text with rotation (INFO and above)
    - app.json.log : JSON-structured with rotation (all levels)
    - error.log : only ERROR and CRITICAL, no rotation limit (for alerting)
    """
    _logger.remove()

    # 1. Stderr – human-readable, coloured
    _logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # 2. Plain text rotating log
    _logger.add(
        LOG_DIR / "app.log",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="50 MB",
        retention="30 days",
        compression="gz",
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    # 3. JSON structured log
    _logger.add(
        LOG_DIR / "app.json.log",
        level="DEBUG",
        format="{message}",
        rotation="100 MB",
        retention="14 days",
        compression="gz",
        serialize=True,   # Loguru's built-in JSON serialisation
        enqueue=True,
    )

    # 4. Dedicated error log – never compressed so it can be tailed easily
    _logger.add(
        LOG_DIR / "error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
        rotation="20 MB",
        retention="90 days",
        compression="gz",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    _logger.info(
        f"Logging initialised | level={settings.LOG_LEVEL} | log_dir={LOG_DIR.resolve()}"
    )


# ── Open JSON file handle used by the custom sink ─────────────────────────────
# We keep this as a module-level resource; it's closed when the process exits.
_json_file_handler = open(LOG_DIR / "app.json.log", "a", encoding="utf-8")  # noqa: WPS515

# Run setup at import time so the logger is ready before any other module uses it.
setup_logging()

# Re-export the configured logger
logger = _logger
