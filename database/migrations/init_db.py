"""
JARVIS Database Initialisation Script.

Creates all tables, inserts default settings, and builds indexes.
Can be run as a standalone script or imported programmatically.
"""

import asyncio
import logging
from typing import Dict, List

from database.models.database import Base, DatabaseManager
from database.models.tables import (
    AccountSnapshot,
    AIModel,
    Alert,
    BacktestResult,
    ChatHistory,
    Settings,
    Strategy,
    Trade,
)

logger = logging.getLogger(__name__)

# Default configuration entries inserted on first initialisation.
DEFAULT_SETTINGS: List[Dict[str, object]] = [
    {"key": "max_risk_percent", "value": "2.0", "encrypted": False},
    {"key": "max_daily_loss_percent", "value": "5.0", "encrypted": False},
    {"key": "max_drawdown_percent", "value": "20.0", "encrypted": False},
    {"key": "max_open_trades", "value": "1", "encrypted": False},
    {"key": "min_risk_reward", "value": "1.0", "encrypted": False},
    {"key": "default_lot_size", "value": "0.01", "encrypted": False},
    {"key": "trading_enabled", "value": "true", "encrypted": False},
    {"key": "telegram_token", "value": "", "encrypted": True},
    {"key": "telegram_chat_id", "value": "", "encrypted": True},
    {"key": "mt5_login", "value": "", "encrypted": True},
    {"key": "mt5_password", "value": "", "encrypted": True},
    {"key": "mt5_server", "value": "", "encrypted": False},
    {"key": "openai_api_key", "value": "", "encrypted": True},
    {"key": "tradingview_webhook_secret", "value": "", "encrypted": True},
    {"key": "allowed_symbols", "value": "EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD", "encrypted": False},
    {"key": "timezone", "value": "UTC", "encrypted": False},
    {"key": "log_level", "value": "INFO", "encrypted": False},
]


async def init_database(
    database_url: str | None = None,
    echo: bool = False,
) -> DatabaseManager:
    """Create tables, insert defaults, and return the DatabaseManager.

    Safe to call multiple times — existing tables and settings are left
    untouched (INSERT OR IGNORE semantics for settings).

    Args:
        database_url: SQLAlchemy async connection string.
        echo: Emit SQL to logs.

    Returns:
        Initialised DatabaseManager instance.
    """
    db = DatabaseManager(database_url=database_url, echo=echo)

    logger.info("Creating database tables …")
    await db.create_all()

    logger.info("Inserting default settings …")
    await _insert_default_settings(db)

    health = await db.health_check()
    if health:
        logger.info("Database initialisation complete — health check OK")
    else:
        logger.error("Database initialisation completed but health check FAILED")

    return db


async def _insert_default_settings(db: DatabaseManager) -> None:
    """Insert default settings rows if they don't already exist."""
    async with db.session() as session:
        for entry in DEFAULT_SETTINGS:
            from sqlalchemy import select

            key = entry["key"]
            stmt = select(Settings).where(Settings.key == key)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is None:
                setting = Settings(
                    key=str(key),
                    value=str(entry.get("value", "")),
                    encrypted=bool(entry.get("encrypted", False)),
                )
                session.add(setting)
                logger.debug("Inserted default setting: %s", key)
            else:
                logger.debug("Setting already exists, skipping: %s", key)


async def reset_database(
    database_url: str | None = None,
    echo: bool = False,
) -> DatabaseManager:
    """Drop and recreate all tables (destructive).

    Use only during development or testing.
    """
    db = DatabaseManager(database_url=database_url, echo=echo)
    logger.warning("Resetting database — dropping all tables")
    await db.drop_all()
    await db.create_all()
    await _insert_default_settings(db)
    logger.info("Database reset complete")
    return db


# ── CLI entry point ──────────────────────────────────────────────────

def main() -> None:
    """Run database initialisation from the command line."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Initialise the JARVIS database")
    parser.add_argument(
        "--url",
        default=None,
        help="Database URL (default: sqlite+aiosqlite:///jarvis.db)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Echo SQL statements",
    )
    args = parser.parse_args()

    coro = reset_database if args.reset else init_database
    asyncio.run(coro(database_url=args.url, echo=args.echo))


if __name__ == "__main__":
    main()
