"""
JARVIS Market Analyzer - Identifies market phases and generates signals
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False
    logger.warning("xgboost not installed – falling back to RandomForest for phase detection")


# ---------------------------------------------------------------------------
# MarketAnalyzer
# ---------------------------------------------------------------------------

class MarketAnalyzer:
    """Analyses market conditions using ML and technical analysis.

    Market phases:
        TRENDING_UP   – sustained upward movement
        TRENDING_DOWN – sustained downward movement
        RANGING       – price oscillates within a band
        VOLATILE      – high ATR / erratic movement
        BREAKOUT      – range compression followed by expansion
    """

    PHASES = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "BREAKOUT"]
    PHASE_INDEX = {p: i for i, p in enumerate(PHASES)}

    def __init__(self):
        if _XGB_AVAILABLE:
            self.classifier = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric="mlogloss",
                verbosity=0,
            )
        else:
            self.classifier = RandomForestClassifier(
                n_estimators=200, max_depth=8, n_jobs=-1, random_state=42
            )
        self.scaler     = StandardScaler()
        self.is_trained = False

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def calculate_indicators(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators and return augmented DataFrame.

        Expects columns: open, high, low, close, volume  (case-insensitive).
        """
        df = ohlcv.copy()
        df.columns = [c.lower() for c in df.columns]

        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        volume = df.get("volume", pd.Series(np.ones(len(df)), index=df.index))

        # --- Moving averages ---
        for p in [5, 10, 20, 50, 100, 200]:
            df[f"ema_{p}"]  = close.ewm(span=p, adjust=False).mean()
            df[f"sma_{p}"]  = close.rolling(p).mean()

        # --- RSI ---
        df["rsi_14"] = self._rsi(close, 14)
        df["rsi_7"]  = self._rsi(close, 7)

        # --- MACD ---
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"]        = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"]   = df["macd"] - df["macd_signal"]

        # --- Bollinger Bands ---
        bb_mid          = close.rolling(20).mean()
        bb_std          = close.rolling(20).std()
        df["bb_upper"]  = bb_mid + 2 * bb_std
        df["bb_lower"]  = bb_mid - 2 * bb_std
        df["bb_mid"]    = bb_mid
        df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / (bb_mid + 1e-10)
        df["bb_pct"]    = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)

        # --- ATR ---
        tr             = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        df["atr_14"]   = tr.ewm(span=14, adjust=False).mean()
        df["atr_7"]    = tr.ewm(span=7,  adjust=False).mean()
        df["atr_pct"]  = df["atr_14"] / (close + 1e-10) * 100

        # --- Stochastic ---
        low_14  = low.rolling(14).min()
        high_14 = high.rolling(14).max()
        df["stoch_k"] = 100 * (close - low_14) / (high_14 - low_14 + 1e-10)
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        # --- ADX ---
        df["adx"] = self._adx(high, low, close, 14)

        # --- Volume ratios ---
        df["vol_sma20"]   = volume.rolling(20).mean()
        df["vol_ratio"]   = volume / (df["vol_sma20"] + 1e-10)
        df["vol_change"]  = volume.pct_change()

        # --- Price momentum ---
        for p in [3, 5, 10, 20]:
            df[f"mom_{p}"] = close.pct_change(p)

        # --- Volatility regime ---
        df["hist_vol_20"] = close.pct_change().rolling(20).std() * np.sqrt(252)

        # --- Trend strength ---
        df["trend_slope_20"] = self._rolling_slope(close, 20)
        df["trend_slope_5"]  = self._rolling_slope(close, 5)

        # --- Higher-timeframe alignment (approximate via SMA ratio) ---
        df["htf_bull"] = (df["ema_20"] > df["ema_50"]).astype(float)

        return df

    # ------------------------------------------------------------------

    def extract_features(self, ohlcv: pd.DataFrame) -> np.ndarray:
        """Extract ML feature matrix from OHLCV data.

        Returns array of shape (N, n_features) – NaN rows are filled with 0.
        """
        df = self.calculate_indicators(ohlcv)

        feature_cols = [
            "rsi_14", "rsi_7",
            "macd", "macd_signal", "macd_hist",
            "bb_width", "bb_pct",
            "atr_pct",
            "stoch_k", "stoch_d",
            "adx",
            "vol_ratio", "vol_change",
            "mom_3", "mom_5", "mom_10", "mom_20",
            "hist_vol_20",
            "trend_slope_20", "trend_slope_5",
            "htf_bull",
        ]
        features = df[feature_cols].fillna(0).values.astype(np.float32)
        return features

    # ------------------------------------------------------------------
    # Market phase detection
    # ------------------------------------------------------------------

    def detect_market_phase(self, ohlcv: pd.DataFrame) -> Dict:
        """Detect the current market phase using either ML or heuristics.

        Returns:
            {
              "phase":       str,
              "confidence":  float,
              "indicators":  dict of relevant indicator values,
              "all_probs":   dict mapping phase → probability,
            }
        """
        df  = self.calculate_indicators(ohlcv)
        row = df.iloc[-1]

        if self.is_trained:
            feat    = self.extract_features(ohlcv)[-1].reshape(1, -1)
            feat_sc = self.scaler.transform(feat)
            probs   = self.classifier.predict_proba(feat_sc)[0]
            phase_idx = int(probs.argmax())
            phase     = self.PHASES[phase_idx]
            confidence = float(probs[phase_idx])
        else:
            phase, confidence, probs = self._heuristic_phase(row)

        return {
            "phase":      phase,
            "confidence": confidence,
            "all_probs":  {p: float(probs[i]) for i, p in enumerate(self.PHASES)},
            "indicators": {
                "rsi":        float(row.get("rsi_14", 0)),
                "adx":        float(row.get("adx",    0)),
                "atr_pct":    float(row.get("atr_pct", 0)),
                "bb_width":   float(row.get("bb_width", 0)),
                "macd":       float(row.get("macd",   0)),
                "vol_ratio":  float(row.get("vol_ratio", 1)),
                "trend_slope": float(row.get("trend_slope_20", 0)),
            },
        }

    def _heuristic_phase(self, row: pd.Series) -> Tuple[str, float, np.ndarray]:
        """Rule-based phase detection when classifier is not trained."""
        adx       = float(row.get("adx",           0))
        rsi       = float(row.get("rsi_14",        50))
        atr_pct   = float(row.get("atr_pct",       0))
        bb_width  = float(row.get("bb_width",      0))
        macd      = float(row.get("macd",          0))
        slope     = float(row.get("trend_slope_20",0))
        vol_ratio = float(row.get("vol_ratio",     1))

        scores = np.zeros(len(self.PHASES))

        # TRENDING_UP
        scores[0] = (
            (1.0 if adx > 25 else 0.0) +
            (1.0 if slope > 0 else 0.0) +
            (0.5 if rsi > 55 else 0.0) +
            (0.5 if macd > 0 else 0.0)
        ) / 3.0

        # TRENDING_DOWN
        scores[1] = (
            (1.0 if adx > 25 else 0.0) +
            (1.0 if slope < 0 else 0.0) +
            (0.5 if rsi < 45 else 0.0) +
            (0.5 if macd < 0 else 0.0)
        ) / 3.0

        # RANGING
        scores[2] = (
            (1.0 if adx < 20 else 0.0) +
            (1.0 if bb_width < 0.03 else 0.0) +
            (0.5 if 40 < rsi < 60 else 0.0)
        ) / 2.5

        # VOLATILE
        scores[3] = (
            (1.0 if atr_pct > 1.0 else 0.0) +
            (0.5 if vol_ratio > 1.5 else 0.0)
        ) / 1.5

        # BREAKOUT
        scores[4] = (
            (1.0 if bb_width > 0.04 and vol_ratio > 1.5 else 0.0) +
            (0.5 if adx > 20 and adx < 30 else 0.0)
        ) / 1.5

        # Normalise to probability-like values
        total = scores.sum() + 1e-10
        probs = scores / total
        phase_idx = int(probs.argmax())
        return self.PHASES[phase_idx], float(probs[phase_idx]), probs

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, ohlcv: pd.DataFrame, market_phase: str) -> Dict:
        """Generate a trading signal appropriate for the given market phase.

        Returns:
            {
              "signal":     "BUY" | "SELL" | "NEUTRAL",
              "confidence": float (0-1),
              "reasoning":  str,
              "entry":      float,
              "sl":         float,
              "tp":         float,
            }
        """
        df  = self.calculate_indicators(ohlcv)
        row = df.iloc[-1]
        close = float(ohlcv["close"].iloc[-1]) if "close" in ohlcv.columns else \
                float(ohlcv["Close"].iloc[-1])

        atr   = float(row.get("atr_14", close * 0.002))
        rsi   = float(row.get("rsi_14", 50))
        macd  = float(row.get("macd",   0))
        stoch = float(row.get("stoch_k", 50))
        adx   = float(row.get("adx",    0))
        slope = float(row.get("trend_slope_20", 0))
        bb_pct= float(row.get("bb_pct", 0.5))

        signal     = "NEUTRAL"
        confidence = 0.0
        reasoning  = ""

        if market_phase in ("TRENDING_UP",):
            if rsi > 50 and macd > 0 and slope > 0:
                signal     = "BUY"
                confidence = min(0.9, (adx / 50) + (rsi - 50) / 100)
                reasoning  = f"Uptrend: ADX={adx:.1f}, RSI={rsi:.1f}, MACD>0, positive slope"
            elif rsi > 75:
                signal     = "NEUTRAL"
                reasoning  = "Uptrend but overbought – wait for pullback"

        elif market_phase == "TRENDING_DOWN":
            if rsi < 50 and macd < 0 and slope < 0:
                signal     = "SELL"
                confidence = min(0.9, (adx / 50) + (50 - rsi) / 100)
                reasoning  = f"Downtrend: ADX={adx:.1f}, RSI={rsi:.1f}, MACD<0, negative slope"

        elif market_phase == "RANGING":
            if bb_pct < 0.1 and rsi < 35 and stoch < 20:
                signal     = "BUY"
                confidence = 0.65
                reasoning  = f"Range bottom: BB%={bb_pct:.2f}, RSI={rsi:.1f}, Stoch={stoch:.1f}"
            elif bb_pct > 0.9 and rsi > 65 and stoch > 80:
                signal     = "SELL"
                confidence = 0.65
                reasoning  = f"Range top: BB%={bb_pct:.2f}, RSI={rsi:.1f}, Stoch={stoch:.1f}"

        elif market_phase == "BREAKOUT":
            if macd > 0 and slope > 0:
                signal     = "BUY"
                confidence = 0.70
                reasoning  = "Bullish breakout confirmed by MACD and positive slope"
            elif macd < 0 and slope < 0:
                signal     = "SELL"
                confidence = 0.70
                reasoning  = "Bearish breakout confirmed by MACD and negative slope"

        elif market_phase == "VOLATILE":
            signal     = "NEUTRAL"
            reasoning  = "High volatility – no trade recommended"
            confidence = 0.0

        sl_dist = atr * 1.5
        tp_dist = atr * 3.0
        sl = close - sl_dist if signal == "BUY" else close + sl_dist if signal == "SELL" else 0.0
        tp = close + tp_dist if signal == "BUY" else close - tp_dist if signal == "SELL" else 0.0

        return {
            "signal":     signal,
            "confidence": float(confidence),
            "reasoning":  reasoning,
            "entry":      close,
            "sl":         float(sl),
            "tp":         float(tp),
        }

    # ------------------------------------------------------------------
    # ICT concepts
    # ------------------------------------------------------------------

    def detect_orderblocks(self, ohlcv: pd.DataFrame) -> List[Dict]:
        """Detect ICT order blocks.

        An order block is the last opposing candle before a strong move.
        Returns a list of dicts with keys:
            index, time, high, low, type ("bullish"|"bearish"), strength
        """
        df = ohlcv.copy()
        df.columns = [c.lower() for c in df.columns]

        obs: List[Dict] = []
        n = len(df)

        for i in range(2, n - 1):
            o1, c1 = df["open"].iloc[i-1], df["close"].iloc[i-1]
            h1      = df["high"].iloc[i-1]
            l1      = df["low"].iloc[i-1]
            o2, c2 = df["open"].iloc[i],   df["close"].iloc[i]

            body1 = abs(c1 - o1)
            body2 = abs(c2 - o2)

            # Bullish OB: bearish candle followed by strong bullish candle
            if c1 < o1 and c2 > o2 and body2 > body1 * 1.5:
                strength = float(body2 / (body1 + 1e-10))
                obs.append({
                    "index":    i - 1,
                    "time":     df.index[i - 1] if hasattr(df.index[0], 'strftime') else i - 1,
                    "high":     float(h1),
                    "low":      float(l1),
                    "type":     "bullish",
                    "strength": round(strength, 2),
                    "mitigated":False,
                })

            # Bearish OB: bullish candle followed by strong bearish candle
            elif c1 > o1 and c2 < o2 and body2 > body1 * 1.5:
                strength = float(body2 / (body1 + 1e-10))
                obs.append({
                    "index":    i - 1,
                    "time":     df.index[i - 1] if hasattr(df.index[0], 'strftime') else i - 1,
                    "high":     float(h1),
                    "low":      float(l1),
                    "type":     "bearish",
                    "strength": round(strength, 2),
                    "mitigated":False,
                })

        # Mark mitigated OBs (price returned to the zone)
        current_close = float(df["close"].iloc[-1])
        for ob in obs:
            if ob["low"] <= current_close <= ob["high"]:
                ob["mitigated"] = True

        return sorted(obs, key=lambda x: x["strength"], reverse=True)[:20]

    def detect_liquidity_sweeps(self, ohlcv: pd.DataFrame) -> List[Dict]:
        """Detect liquidity sweeps (stop hunts above/below swing highs/lows).

        Returns list of dicts:
            index, time, price, type ("buy_side"|"sell_side"), swept_level
        """
        df = ohlcv.copy()
        df.columns = [c.lower() for c in df.columns]

        sweeps: List[Dict] = []
        swing_lookback = 10

        for i in range(swing_lookback + 1, len(df) - 1):
            high_window = df["high"].iloc[i - swing_lookback: i]
            low_window  = df["low"].iloc[i  - swing_lookback: i]

            swing_high = float(high_window.max())
            swing_low  = float(low_window.min())

            curr_high  = float(df["high"].iloc[i])
            curr_low   = float(df["low"].iloc[i])
            curr_close = float(df["close"].iloc[i])

            # Buy-side liquidity sweep: wick above swing high then close below
            if curr_high > swing_high and curr_close < swing_high:
                sweeps.append({
                    "index":       i,
                    "time":        df.index[i] if hasattr(df.index[0], 'strftime') else i,
                    "price":       curr_high,
                    "type":        "buy_side",
                    "swept_level": swing_high,
                    "close":       curr_close,
                })

            # Sell-side liquidity sweep: wick below swing low then close above
            if curr_low < swing_low and curr_close > swing_low:
                sweeps.append({
                    "index":       i,
                    "time":        df.index[i] if hasattr(df.index[0], 'strftime') else i,
                    "price":       curr_low,
                    "type":        "sell_side",
                    "swept_level": swing_low,
                    "close":       curr_close,
                })

        return sweeps[-20:]

    def detect_fair_value_gaps(self, ohlcv: pd.DataFrame,
                               min_size_pct: float = 0.001) -> List[Dict]:
        """Detect Fair Value Gaps (FVG / imbalance areas).

        A bullish FVG exists when candle[i-1].high < candle[i+1].low
        A bearish FVG exists when candle[i-1].low  > candle[i+1].high

        Returns list of dicts:
            index, time, upper, lower, type ("bullish"|"bearish"), size_pct, filled
        """
        df = ohlcv.copy()
        df.columns = [c.lower() for c in df.columns]
        fvgs: List[Dict] = []
        current_close = float(df["close"].iloc[-1])

        for i in range(1, len(df) - 1):
            h_prev = float(df["high"].iloc[i - 1])
            l_prev = float(df["low"].iloc[i - 1])
            h_next = float(df["high"].iloc[i + 1])
            l_next = float(df["low"].iloc[i + 1])
            mid    = float(df["close"].iloc[i])

            # Bullish FVG
            if l_next > h_prev:
                size_pct = (l_next - h_prev) / (mid + 1e-10)
                if size_pct >= min_size_pct:
                    filled = l_next >= current_close >= h_prev
                    fvgs.append({
                        "index":    i,
                        "time":     df.index[i] if hasattr(df.index[0], 'strftime') else i,
                        "upper":    l_next,
                        "lower":    h_prev,
                        "type":     "bullish",
                        "size_pct": round(size_pct * 100, 4),
                        "filled":   filled,
                    })

            # Bearish FVG
            elif h_next < l_prev:
                size_pct = (l_prev - h_next) / (mid + 1e-10)
                if size_pct >= min_size_pct:
                    filled = h_next <= current_close <= l_prev
                    fvgs.append({
                        "index":    i,
                        "time":     df.index[i] if hasattr(df.index[0], 'strftime') else i,
                        "upper":    l_prev,
                        "lower":    h_next,
                        "type":     "bearish",
                        "size_pct": round(size_pct * 100, 4),
                        "filled":   filled,
                    })

        # Return most recent unfilled FVGs first
        unfilled = [f for f in fvgs if not f["filled"]]
        return sorted(unfilled, key=lambda x: x["index"], reverse=True)[:20]

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, historical_data: pd.DataFrame, labels: np.ndarray) -> None:
        """Train the market-phase classifier.

        Args:
            historical_data: OHLCV DataFrame.
            labels:          Integer array mapping each row to a phase index
                             (use PHASE_INDEX to map strings to ints).
        """
        features = self.extract_features(historical_data)
        # Align lengths (indicators need a warm-up period)
        min_len  = min(len(features), len(labels))
        X = features[-min_len:]
        y = labels[-min_len:]

        X_sc = self.scaler.fit_transform(X)
        self.classifier.fit(X_sc, y)
        self.is_trained = True
        logger.info(f"MarketAnalyzer trained on {min_len} samples.")

    def save(self, path: str) -> None:
        """Persist classifier and scaler to disk."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump({"classifier": self.classifier, "scaler": self.scaler,
                         "is_trained": self.is_trained}, f)
        logger.info(f"MarketAnalyzer saved: {p}")

    def load(self, path: str) -> None:
        """Load classifier and scaler from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.classifier = data["classifier"]
        self.scaler     = data["scaler"]
        self.is_trained = data.get("is_trained", True)
        logger.info(f"MarketAnalyzer loaded: {path}")

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta  = series.diff()
        gain   = delta.clip(lower=0)
        loss   = (-delta).clip(lower=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs  = avg_gain / (avg_loss + 1e-10)
        return 100 - 100 / (1 + rs)

    @staticmethod
    def _adx(high: pd.Series, low: pd.Series,
             close: pd.Series, period: int = 14) -> pd.Series:
        tr  = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs(),
        ], axis=1).max(axis=1)

        dm_plus  = high.diff().clip(lower=0)
        dm_minus = (-low.diff()).clip(lower=0)
        # Where +DM < -DM or -DM < +DM, zero out the lesser
        cond = dm_plus >= dm_minus
        dm_plus  = dm_plus.where(cond,  0.0)
        dm_minus = dm_minus.where(~cond, 0.0)

        atr_s   = tr.ewm(span=period, adjust=False).mean()
        dip     = 100 * dm_plus.ewm(span=period, adjust=False).mean() / (atr_s + 1e-10)
        din     = 100 * dm_minus.ewm(span=period, adjust=False).mean() / (atr_s + 1e-10)
        dx      = 100 * (dip - din).abs() / (dip + din + 1e-10)
        adx     = dx.ewm(span=period, adjust=False).mean()
        return adx

    @staticmethod
    def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
        """Approximate linear slope of `series` over `window` bars, normalised."""
        slopes = [np.nan] * (window - 1)
        vals   = series.values
        for i in range(window - 1, len(vals)):
            y = vals[i - window + 1: i + 1]
            x = np.arange(window, dtype=float)
            slope = np.polyfit(x, y, 1)[0]
            # Normalise by mean price
            slopes.append(slope / (np.mean(y) + 1e-10))
        return pd.Series(slopes, index=series.index)
