"""Alembic migration environment for the JARVIS Trading OS.

Supports both offline (SQL script generation) and online (direct DB connection)
migration modes.  The target metadata is pulled from the application's
``Base.metadata`` so that ``alembic revision --autogenerate`` can diff the
current schema against the ORM models.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the project root is on sys.path so we can import app modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import settings  # noqa: E402
from backend.app.core.database import Base  # noqa: E402

# Import all models so they register with Base.metadata.
import backend.app.models.trade  # noqa: E402, F401

config = context.config

if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
