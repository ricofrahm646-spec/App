"""Base strategy interface for JARVIS AI Trading OS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import pandas as pd


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass(frozen=True)
class Signal:
    """Represents a trading signal emitted by a strategy."""

    direction: Direction
    confidence: float  # 0.0 – 1.0
    entry_price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


class BaseStrategy(ABC):
    """Abstract base class every strategy must implement."""

    _parameters: Dict[str, Any]

    def __init__(self, parameters: Optional[Dict[str, Any]] = None) -> None:
        self._parameters = parameters or self._default_parameters()

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        """Evaluate *data* and return a :class:`Signal`.

        *data* must contain at least ``open``, ``high``, ``low``, ``close``
        columns.  Additional columns (``volume``, indicators, etc.) are
        strategy-specific.
        """

    @abstractmethod
    def _default_parameters(self) -> Dict[str, Any]:
        """Return the strategy's factory-default parameter set."""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the strategy logic."""

    # ------------------------------------------------------------------
    # Parameter helpers
    # ------------------------------------------------------------------

    def get_parameters(self) -> Dict[str, Any]:
        return dict(self._parameters)

    def set_parameters(self, params: Dict[str, Any]) -> None:
        self._parameters.update(params)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self._parameters})>"
