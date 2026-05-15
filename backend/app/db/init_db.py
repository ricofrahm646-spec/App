"""Create tables on first start (lightweight alternative to Alembic for dev)."""
from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.logging_setup import logger
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.db import models  # noqa: F401  (register models)


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialised")
    except SQLAlchemyError as exc:  # pragma: no cover - integration path
        logger.warning("Database init skipped: {}", exc)
