"""Strategy registry — maps kind → class and supports plugin registration."""
from __future__ import annotations

from typing import Any

from strategies.base import Strategy

_REGISTRY: dict[str, type[Strategy]] = {}


def register(kind: str):
    def decorator(cls: type[Strategy]) -> type[Strategy]:
        cls.kind = kind
        _REGISTRY[kind] = cls
        return cls

    return decorator


def list_kinds() -> list[str]:
    _ensure_loaded()
    return sorted(_REGISTRY.keys())


def get_strategy(kind: str, **parameters: Any) -> Strategy:
    _ensure_loaded()
    if kind not in _REGISTRY:
        raise KeyError(f"Unknown strategy kind '{kind}'. Available: {list_kinds()}")
    return _REGISTRY[kind](**parameters)


_LOADED = False


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    # Import the strategy modules so their @register decorators fire.
    from strategies import (  # noqa: F401
        breakout,
        ict,
        mean_reversion,
        momentum,
        scalping,
        session_trading,
        smart_money,
        trend_following,
    )

    _LOADED = True
