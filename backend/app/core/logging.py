import logging
from logging.config import dictConfig
from pathlib import Path


def configure_logging() -> None:
    Path("logging").mkdir(exist_ok=True)
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"},
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": "logging/jarvis.log",
                    "maxBytes": 5_000_000,
                    "backupCount": 5,
                },
            },
            "root": {"handlers": ["console", "file"], "level": "INFO"},
        }
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
