"""Shared dependencies."""

from functools import lru_cache

from app.services.mt5_connector import MT5Connector


@lru_cache
def get_mt5() -> MT5Connector:
    return MT5Connector()
