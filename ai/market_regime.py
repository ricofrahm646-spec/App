from enum import StrEnum

import numpy as np


class MarketRegime(StrEnum):
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"


class MarketRegimeClassifier:
    def classify(self, closes: list[float], volumes: list[float] | None = None) -> MarketRegime:
        if len(closes) < 20:
            return MarketRegime.LOW_LIQUIDITY

        returns = np.diff(np.array(closes)) / np.array(closes[:-1])
        volatility = float(np.std(returns))
        trend_strength = abs(float(closes[-1] - closes[0])) / max(closes[0], 1e-9)

        if volumes and float(np.mean(volumes[-10:])) <= 0:
            return MarketRegime.LOW_LIQUIDITY
        if volatility > 0.02:
            return MarketRegime.HIGH_VOLATILITY
        if trend_strength > 0.03:
            return MarketRegime.TRENDING
        return MarketRegime.RANGING
