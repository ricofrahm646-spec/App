"""Strategy registry – maps strategy type names to classes."""

from typing import Dict, Type, Optional
from .base import BaseStrategy, StrategyConfig
from .scalping import ScalpingStrategy
from .ict import ICTStrategy
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "SCALPING": ScalpingStrategy,
    "ICT": ICTStrategy,
    "TREND": TrendFollowingStrategy,
    "MEAN_REVERSION": MeanReversionStrategy,
}


def get_strategy(strategy_type: str, config: Optional[StrategyConfig] = None) -> BaseStrategy:
    """Instantiate a strategy by type name."""
    cls = STRATEGY_REGISTRY.get(strategy_type.upper())
    if cls is None:
        available = list(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy type '{strategy_type}'. Available: {available}")
    return cls(config=config)


def list_strategies() -> list:
    """Return metadata for all registered strategies."""
    result = []
    for key, cls in STRATEGY_REGISTRY.items():
        instance = cls()
        result.append({
            "type": key,
            "name": instance.name,
            "version": instance.version,
            "description": instance.description,
        })
    return result
