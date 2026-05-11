"""Trading strategies used by the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Protocol


@dataclass(slots=True)
class StrategySignal:
    """Represents trading instruction for a single price step."""

    index: int
    action: str
    confidence: float
    reason: str


class TradingStrategy(Protocol):
    """Protocol for strategy implementations."""

    name: str
    parameters: dict[str, float]

    def generate_signals(self, prices: list[float]) -> list[StrategySignal]:
        """Create signals from historical prices."""


def _ema(values: list[float], period: int) -> list[float]:
    if period <= 0:
        raise ValueError("period must be positive")
    alpha = 2 / (period + 1)
    result: list[float] = []
    current = values[0]
    for price in values:
        current = alpha * price + (1 - alpha) * current
        result.append(current)
    return result


@dataclass(slots=True)
class EmaStrategy:
    """EMA crossover strategy."""

    short_period: int = 12
    long_period: int = 26
    name: str = "ema"

    @property
    def parameters(self) -> dict[str, float]:
        return {"short_period": float(self.short_period), "long_period": float(self.long_period)}

    def generate_signals(self, prices: list[float]) -> list[StrategySignal]:
        short = _ema(prices, self.short_period)
        long = _ema(prices, self.long_period)
        signals: list[StrategySignal] = []
        for i in range(1, len(prices)):
            if short[i] > long[i] and short[i - 1] <= long[i - 1]:
                signals.append(StrategySignal(i, "buy", 0.72, "EMA bullish crossover"))
            elif short[i] < long[i] and short[i - 1] >= long[i - 1]:
                signals.append(StrategySignal(i, "sell", 0.72, "EMA bearish crossover"))
        return signals


@dataclass(slots=True)
class RsiStrategy:
    """RSI threshold strategy."""

    period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0
    name: str = "rsi"

    @property
    def parameters(self) -> dict[str, float]:
        return {
            "period": float(self.period),
            "overbought": self.overbought,
            "oversold": self.oversold,
        }

    def generate_signals(self, prices: list[float]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        if len(prices) <= self.period:
            return signals
        for i in range(self.period, len(prices)):
            gains: list[float] = []
            losses: list[float] = []
            for j in range(i - self.period + 1, i + 1):
                delta = prices[j] - prices[j - 1]
                gains.append(max(delta, 0))
                losses.append(abs(min(delta, 0)))
            avg_gain = mean(gains)
            avg_loss = mean(losses) or 1e-9
            rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
            if rsi <= self.oversold:
                signals.append(StrategySignal(i, "buy", 0.69, f"RSI {rsi:.2f} oversold"))
            elif rsi >= self.overbought:
                signals.append(StrategySignal(i, "sell", 0.69, f"RSI {rsi:.2f} overbought"))
        return signals


@dataclass(slots=True)
class BreakoutStrategy:
    """Price breakout strategy."""

    lookback: int = 20
    name: str = "breakout"

    @property
    def parameters(self) -> dict[str, float]:
        return {"lookback": float(self.lookback)}

    def generate_signals(self, prices: list[float]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        if len(prices) <= self.lookback:
            return signals
        for i in range(self.lookback, len(prices)):
            window = prices[i - self.lookback : i]
            highest = max(window)
            lowest = min(window)
            current = prices[i]
            if current > highest:
                signals.append(StrategySignal(i, "buy", 0.75, "Breakout above local resistance"))
            elif current < lowest:
                signals.append(StrategySignal(i, "sell", 0.75, "Breakdown below local support"))
        return signals


@dataclass(slots=True)
class MeanReversionStrategy:
    """Mean reversion strategy using rolling average distance."""

    lookback: int = 15
    threshold: float = 0.03
    name: str = "mean_reversion"

    @property
    def parameters(self) -> dict[str, float]:
        return {"lookback": float(self.lookback), "threshold": self.threshold}

    def generate_signals(self, prices: list[float]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        if len(prices) <= self.lookback:
            return signals
        for i in range(self.lookback, len(prices)):
            window = prices[i - self.lookback : i]
            moving_average = mean(window)
            current = prices[i]
            deviation = (current - moving_average) / moving_average
            if deviation <= -self.threshold:
                signals.append(StrategySignal(i, "buy", 0.66, "Price below rolling mean"))
            elif deviation >= self.threshold:
                signals.append(StrategySignal(i, "sell", 0.66, "Price above rolling mean"))
        return signals

