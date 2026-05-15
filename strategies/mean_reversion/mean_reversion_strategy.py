"""Mean reversion strategy using Bollinger Bands + RSI divergence."""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal, Direction

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Trades reversals back to the mean using Bollinger Bands + RSI oversold/overbought."""

    @property
    def name(self) -> str:
        return "Mean Reversion Strategy"

    @property
    def description(self) -> str:
        return "Bollinger Band reversal with RSI confirmation, targeting the moving average"

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "bb_period": 20,
            "bb_std": 2.0,
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "atr_period": 14,
            "sl_atr_mult": 1.5,
            "tp_to_mean": True,
        }

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        min_len = max(p["bb_period"], p["rsi_period"], p["atr_period"]) + 5

        if len(data) < min_len:
            return Signal(direction=Direction.NONE, confidence=0.0)

        close = data["close"]
        high = data["high"]
        low = data["low"]

        sma = close.rolling(p["bb_period"]).mean()
        std = close.rolling(p["bb_period"]).std()
        upper_band = sma + p["bb_std"] * std
        lower_band = sma - p["bb_std"] * std

        rsi = self._rsi(close, p["rsi_period"])

        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(p["atr_period"]).mean()

        cur_close = close.iloc[-1]
        cur_rsi = rsi.iloc[-1]
        cur_lower = lower_band.iloc[-1]
        cur_upper = upper_band.iloc[-1]
        cur_sma = sma.iloc[-1]
        cur_atr = atr.iloc[-1]

        if any(np.isnan(v) for v in [cur_rsi, cur_lower, cur_upper, cur_sma, cur_atr]):
            return Signal(direction=Direction.NONE, confidence=0.0)

        if cur_close <= cur_lower and cur_rsi < p["rsi_oversold"]:
            sl = cur_close - cur_atr * p["sl_atr_mult"]
            tp = cur_sma if p["tp_to_mean"] else cur_close + cur_atr * 2.0
            band_dist = (cur_lower - cur_close) / cur_atr if cur_atr > 0 else 0
            conf = min(0.9, 0.5 + band_dist * 0.15 + (p["rsi_oversold"] - cur_rsi) / 100 * 0.3)
            return Signal(
                direction=Direction.BUY,
                confidence=round(max(conf, 0.35), 3),
                entry_price=cur_close,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        if cur_close >= cur_upper and cur_rsi > p["rsi_overbought"]:
            sl = cur_close + cur_atr * p["sl_atr_mult"]
            tp = cur_sma if p["tp_to_mean"] else cur_close - cur_atr * 2.0
            band_dist = (cur_close - cur_upper) / cur_atr if cur_atr > 0 else 0
            conf = min(0.9, 0.5 + band_dist * 0.15 + (cur_rsi - p["rsi_overbought"]) / 100 * 0.3)
            return Signal(
                direction=Direction.SELL,
                confidence=round(max(conf, 0.35), 3),
                entry_price=cur_close,
                sl=round(sl, 5),
                tp=round(tp, 5),
            )

        return Signal(direction=Direction.NONE, confidence=0.0)
