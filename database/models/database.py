"""
JARVIS Database Connection & Session Management.

Provides async SQLAlchemy engine setup, session factory,
declarative base, and migration helpers.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

logger = logging.getLogger(__name__)

_DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///jarvis.db"

# Pool configuration
_POOL_SIZE = 5
_MAX_OVERFLOW = 10
_POOL_TIMEOUT = 30
_POOL_RECYCLE = 1800  # seconds


class Base(DeclarativeBase):
    """Declarative base for all JARVIS ORM models."""
    pass


class DatabaseManager:
    """Manages the async database engine and session lifecycle."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: bool = False,
    ) -> None:
        """
        Args:
            database_url: SQLAlchemy async connection string.
            echo: When True, emit SQL statements to the log.
        """
        self._database_url = database_url or _DEFAULT_DATABASE_URL
        self._echo = echo
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    # ── Engine & session factory ─────────────────────────────────────

    def _create_engine(self) -> AsyncEngine:
        connect_args = {}
        pool_class = AsyncAdaptedQueuePool

        if self._database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            pool_class = None  # type: ignore[assignment]

        kwargs = dict(
            echo=self._echo,
            future=True,
        )
        if pool_class is not None:
            kwargs.update(
                poolclass=pool_class,
                pool_size=_POOL_SIZE,
                max_overflow=_MAX_OVERFLOW,
                pool_timeout=_POOL_TIMEOUT,
                pool_recycle=_POOL_RECYCLE,
            )

        engine = create_async_engine(
            self._database_url,
            connect_args=connect_args,
            **kwargs,
        )
        logger.info("Database engine created: %s", self._database_url)
        return engine

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    # ── Session context manager ──────────────────────────────────────

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional session scope.

        Commits on success, rolls back on exception.
        """
        async with self.session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    # ── Schema management ────────────────────────────────────────────

    async def create_all(self) -> None:
        """Create all tables defined in the ORM metadata."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created")

    async def drop_all(self) -> None:
        """Drop all ORM-managed tables (use with caution)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")

    async def table_exists(self, table_name: str) -> bool:
        """Check whether a given table exists in the database."""
        async with self.engine.connect() as conn:
            result = await conn.run_sync(
                lambda sync_conn: Base.metadata.tables.get(table_name) is not None
            )
        return bool(result)

    # ── Health check ─────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Return True if the database is reachable."""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("Database health check failed")
            return False

    # ── Lifecycle ────────────────────────────────────────────────────

    async def close(self) -> None:
        """Dispose of the engine and release connection pool."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database engine disposed")

    async def __aenter__(self) -> "DatabaseManager":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()
