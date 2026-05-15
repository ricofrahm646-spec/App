"""Multi-MA trend-following strategy with ADX filter."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, Direction, Signal


class TrendFollowingStrategy(BaseStrategy):
    """Trend-following strategy using multiple moving averages.

    Entry when short, medium, and long MAs are aligned in trend direction.
    ADX must exceed a threshold to confirm trend strength.
    ATR is used for dynamic SL / TP placement.
    An optional higher-timeframe EMA bias filter can further reduce
    counter-trend entries.
    """

    @property
    def name(self) -> str:
        return "Trend Following"

    @property
    def description(self) -> str:
        return (
            "Triple moving-average alignment with ADX trend-strength filter "
            "and ATR-based dynamic stop-loss / take-profit levels."
        )

    def _default_parameters(self) -> Dict[str, Any]:
        return {
            "short_ma": 20,
            "medium_ma": 50,
            "long_ma": 200,
            "adx_period": 14,
            "adx_threshold": 25,
            "atr_period": 14,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 3.0,
            "htf_ema_period": 200,
            "use_htf_filter": True,
        }

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Signal:
        p = self._parameters
        min_bars = max(p["long_ma"], p["htf_ema_period"]) + p["adx_period"] + 5
        if len(data) < min_bars:
            return Signal(direction=Direction.NONE, confidence=0.0)

        close = data["close"]
        high = data["high"]
        low = data["low"]

        short_ma = close.rolling(p["short_ma"]).mean()
        medium_ma = close.rolling(p["medium_ma"]).mean()
        long_ma = close.rolling(p["long_ma"]).mean()

        adx = self._adx(high, low, close, p["adx_period"])
        atr = self._atr(high, low, close, p["atr_period"])

        if adx is None or atr is None:
            return Signal(direction=Direction.NONE, confidence=0.0)

        current_adx = adx.iloc[-1]
        current_atr = atr.iloc[-1]
        price = float(close.iloc[-1])

        if current_adx < p["adx_threshold"]:
            return Signal(direction=Direction.NONE, confidence=0.0)

        s = float(short_ma.iloc[-1])
        m = float(medium_ma.iloc[-1])
        l_ = float(long_ma.iloc[-1])

        bullish_aligned = s > m > l_
        bearish_aligned = s < m < l_

        # Optional higher-timeframe filter
        if p["use_htf_filter"]:
            htf_ema = close.ewm(span=p["htf_ema_period"], adjust=False).mean()
            htf_val = htf_ema.iloc[-1]
            if bullish_aligned and price < htf_val:
                bullish_aligned = False
            if bearish_aligned and price > htf_val:
                bearish_aligned = False

        if not bullish_aligned and not bearish_aligned:
            return Signal(direction=Direction.NONE, confidence=0.0)

        confidence = self._compute_confidence(current_adx, s, m, l_, price)
        sl_dist = current_atr * p["atr_sl_mult"]
        tp_dist = current_atr * p["atr_tp_mult"]

        if bullish_aligned:
            return Signal(
                direction=Direction.BUY,
                confidence=confidence,
                entry_price=price,
                sl=price - sl_dist,
                tp=price + tp_dist,
            )
        else:
            return Signal(
                direction=Direction.SELL,
                confidence=confidence,
                entry_price=price,
                sl=price + sl_dist,
                tp=price - tp_dist,
            )

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    @staticmethod
    def _adx(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int
    ) -> Optional[pd.Series]:
        if len(close) < period * 2:
            return None

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        plus_di = 100 * (
            plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr
        )
        minus_di = 100 * (
            minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr
        )

        dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
        adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        return adx

    @staticmethod
    def _atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int
    ) -> Optional[pd.Series]:
        if len(close) < period + 1:
            return None
        tr = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    @staticmethod
    def _compute_confidence(
        adx: float, short: float, medium: float, long: float, price: float
    ) -> float:
        adx_score = min(adx / 50, 1.0) * 0.5

        spread = abs(short - long) / price if price else 0
        alignment_score = min(spread * 100, 1.0) * 0.3

        proximity = 1 - abs(price - short) / (abs(price - long) + 1e-10)
        proximity_score = max(min(proximity, 1.0), 0.0) * 0.2

        return float(np.clip(adx_score + alignment_score + proximity_score, 0.1, 1.0))
