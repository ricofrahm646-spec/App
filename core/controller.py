"""
J.A.R.V.I.S. V300 - CHART VISION CONTROLLER
Screen capture and chart pattern analysis via OpenCV.
Detects candlestick patterns, support/resistance levels,
and trend structures from MT5 chart screenshots.

NOTE: Game cheating features (e.g. aimbots) are intentionally
excluded. This module focuses exclusively on chart analysis.
"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger("JARVIS.Controller")


class PatternType(Enum):
    DOJI = "Doji"
    HAMMER = "Hammer"
    ENGULFING_BULL = "Bullish Engulfing"
    ENGULFING_BEAR = "Bearish Engulfing"
    MORNING_STAR = "Morning Star"
    EVENING_STAR = "Evening Star"
    PINBAR_BULL = "Bullish Pin Bar"
    PINBAR_BEAR = "Bearish Pin Bar"
    DOUBLE_TOP = "Double Top"
    DOUBLE_BOTTOM = "Double Bottom"
    SUPPORT = "Support Level"
    RESISTANCE = "Resistance Level"
    TREND_UP = "Uptrend"
    TREND_DOWN = "Downtrend"
    CONSOLIDATION = "Consolidation"


@dataclass
class DetectedPattern:
    pattern_type: PatternType
    confidence: float
    location: tuple  # (x, y) on screen or candle index
    timestamp: datetime
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ScreenCapture:
    """Captures screen regions for chart analysis."""

    def __init__(self):
        self._mss = None

    def _init_mss(self):
        if self._mss is not None:
            return True
        try:
            import mss
            self._mss = mss.mss()
            return True
        except ImportError:
            logger.warning("mss not available - screen capture disabled")
            return False
        except Exception as e:
            logger.warning(f"Screen capture init failed: {e}")
            return False

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        if not self._init_mss():
            return None

        monitor = {"top": y, "left": x, "width": width, "height": height}
        try:
            screenshot = self._mss.grab(monitor)
            return np.array(screenshot)
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None

    def capture_full_screen(self) -> Optional[np.ndarray]:
        if not self._init_mss():
            return None

        try:
            monitor = self._mss.monitors[1]
            screenshot = self._mss.grab(monitor)
            return np.array(screenshot)
        except Exception as e:
            logger.error(f"Full screen capture failed: {e}")
            return None


class ChartPatternDetector:
    """Detects candlestick patterns and chart structures from OHLC data."""

    def __init__(self):
        self.patterns_detected: list[DetectedPattern] = []

    def analyze_candles(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> list[DetectedPattern]:
        self.patterns_detected = []

        if len(opens) < 3:
            return self.patterns_detected

        self._detect_doji(opens, highs, lows, closes)
        self._detect_hammer(opens, highs, lows, closes)
        self._detect_engulfing(opens, highs, lows, closes)
        self._detect_pinbar(opens, highs, lows, closes)
        self._detect_support_resistance(highs, lows)
        self._detect_trend(closes)

        return self.patterns_detected

    def _detect_doji(self, opens, highs, lows, closes):
        for i in range(len(opens)):
            body = abs(closes[i] - opens[i])
            total_range = highs[i] - lows[i]
            if total_range == 0:
                continue
            if body / total_range < 0.1:
                self.patterns_detected.append(DetectedPattern(
                    pattern_type=PatternType.DOJI,
                    confidence=1.0 - (body / total_range),
                    location=(i, closes[i]),
                    timestamp=datetime.now(),
                ))

    def _detect_hammer(self, opens, highs, lows, closes):
        for i in range(len(opens)):
            body = abs(closes[i] - opens[i])
            lower_wick = min(opens[i], closes[i]) - lows[i]
            upper_wick = highs[i] - max(opens[i], closes[i])
            total_range = highs[i] - lows[i]

            if total_range == 0 or body == 0:
                continue

            if lower_wick >= body * 2 and upper_wick <= body * 0.5:
                self.patterns_detected.append(DetectedPattern(
                    pattern_type=PatternType.HAMMER,
                    confidence=min(lower_wick / (body * 2), 1.0),
                    location=(i, lows[i]),
                    timestamp=datetime.now(),
                ))

    def _detect_engulfing(self, opens, highs, lows, closes):
        for i in range(1, len(opens)):
            prev_body = abs(closes[i - 1] - opens[i - 1])
            curr_body = abs(closes[i] - opens[i])

            if curr_body <= prev_body:
                continue

            is_prev_bear = closes[i - 1] < opens[i - 1]
            is_curr_bull = closes[i] > opens[i]

            if is_prev_bear and is_curr_bull and closes[i] > opens[i - 1] and opens[i] < closes[i - 1]:
                self.patterns_detected.append(DetectedPattern(
                    pattern_type=PatternType.ENGULFING_BULL,
                    confidence=min(curr_body / prev_body / 2, 1.0),
                    location=(i, closes[i]),
                    timestamp=datetime.now(),
                ))

            is_prev_bull = closes[i - 1] > opens[i - 1]
            is_curr_bear = closes[i] < opens[i]

            if is_prev_bull and is_curr_bear and closes[i] < opens[i - 1] and opens[i] > closes[i - 1]:
                self.patterns_detected.append(DetectedPattern(
                    pattern_type=PatternType.ENGULFING_BEAR,
                    confidence=min(curr_body / prev_body / 2, 1.0),
                    location=(i, closes[i]),
                    timestamp=datetime.now(),
                ))

    def _detect_pinbar(self, opens, highs, lows, closes):
        for i in range(len(opens)):
            body = abs(closes[i] - opens[i])
            lower_wick = min(opens[i], closes[i]) - lows[i]
            upper_wick = highs[i] - max(opens[i], closes[i])
            total_range = highs[i] - lows[i]

            if total_range == 0 or body == 0:
                continue

            if lower_wick >= body * 2.5 and upper_wick < body:
                self.patterns_detected.append(DetectedPattern(
                    pattern_type=PatternType.PINBAR_BULL,
                    confidence=min(lower_wick / (body * 3), 1.0),
                    location=(i, lows[i]),
                    timestamp=datetime.now(),
                ))

            if upper_wick >= body * 2.5 and lower_wick < body:
                self.patterns_detected.append(DetectedPattern(
                    pattern_type=PatternType.PINBAR_BEAR,
                    confidence=min(upper_wick / (body * 3), 1.0),
                    location=(i, highs[i]),
                    timestamp=datetime.now(),
                ))

    def _detect_support_resistance(self, highs, lows, tolerance_pct: float = 0.001):
        if len(highs) < 10:
            return

        window = min(5, len(highs) // 3)
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i - window:i + window + 1]):
                touches = sum(1 for h in highs if abs(h - highs[i]) / highs[i] < tolerance_pct)
                if touches >= 2:
                    self.patterns_detected.append(DetectedPattern(
                        pattern_type=PatternType.RESISTANCE,
                        confidence=min(touches / 4, 1.0),
                        location=(i, highs[i]),
                        timestamp=datetime.now(),
                        metadata={"level": float(highs[i]), "touches": touches},
                    ))

            if lows[i] == min(lows[i - window:i + window + 1]):
                touches = sum(1 for l in lows if abs(l - lows[i]) / lows[i] < tolerance_pct)
                if touches >= 2:
                    self.patterns_detected.append(DetectedPattern(
                        pattern_type=PatternType.SUPPORT,
                        confidence=min(touches / 4, 1.0),
                        location=(i, lows[i]),
                        timestamp=datetime.now(),
                        metadata={"level": float(lows[i]), "touches": touches},
                    ))

    def _detect_trend(self, closes, window: int = 20):
        if len(closes) < window:
            return

        recent = closes[-window:]
        x = np.arange(window)
        slope = np.polyfit(x, recent, 1)[0]
        normalized_slope = slope / np.mean(recent)

        if normalized_slope > 0.0001:
            self.patterns_detected.append(DetectedPattern(
                pattern_type=PatternType.TREND_UP,
                confidence=min(abs(normalized_slope) * 1000, 1.0),
                location=(len(closes) - 1, closes[-1]),
                timestamp=datetime.now(),
                metadata={"slope": float(normalized_slope)},
            ))
        elif normalized_slope < -0.0001:
            self.patterns_detected.append(DetectedPattern(
                pattern_type=PatternType.TREND_DOWN,
                confidence=min(abs(normalized_slope) * 1000, 1.0),
                location=(len(closes) - 1, closes[-1]),
                timestamp=datetime.now(),
                metadata={"slope": float(normalized_slope)},
            ))
        else:
            self.patterns_detected.append(DetectedPattern(
                pattern_type=PatternType.CONSOLIDATION,
                confidence=1.0 - min(abs(normalized_slope) * 5000, 1.0),
                location=(len(closes) - 1, closes[-1]),
                timestamp=datetime.now(),
            ))


class ChartImageAnalyzer:
    """Analyzes chart screenshots using OpenCV for visual pattern detection."""

    def __init__(self):
        self.cv2 = None

    def _init_cv2(self):
        if self.cv2 is not None:
            return True
        try:
            import cv2
            self.cv2 = cv2
            return True
        except ImportError:
            logger.warning("OpenCV not available - image analysis disabled")
            return False

    def detect_candles_from_image(self, image: np.ndarray) -> list[dict]:
        """Extract candlestick data from a chart screenshot via color segmentation."""
        if not self._init_cv2():
            return []

        hsv = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2HSV)

        green_lower = np.array([35, 50, 50])
        green_upper = np.array([85, 255, 255])
        red_lower1 = np.array([0, 50, 50])
        red_upper1 = np.array([10, 255, 255])
        red_lower2 = np.array([170, 50, 50])
        red_upper2 = np.array([180, 255, 255])

        green_mask = self.cv2.inRange(hsv, green_lower, green_upper)
        red_mask = self.cv2.inRange(hsv, red_lower1, red_upper1) | self.cv2.inRange(hsv, red_lower2, red_upper2)

        green_contours, _ = self.cv2.findContours(green_mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
        red_contours, _ = self.cv2.findContours(red_mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)

        candles = []
        for cnt in green_contours:
            x, y, w, h = self.cv2.boundingRect(cnt)
            if h > 5 and w > 2:
                candles.append({"x": x, "y": y, "w": w, "h": h, "type": "bullish"})

        for cnt in red_contours:
            x, y, w, h = self.cv2.boundingRect(cnt)
            if h > 5 and w > 2:
                candles.append({"x": x, "y": y, "w": w, "h": h, "type": "bearish"})

        candles.sort(key=lambda c: c["x"])
        return candles

    def detect_horizontal_lines(self, image: np.ndarray) -> list[dict]:
        """Detect horizontal support/resistance lines drawn on chart."""
        if not self._init_cv2():
            return []

        gray = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
        edges = self.cv2.Canny(gray, 50, 150)

        lines = self.cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
        if lines is None:
            return []

        horizontal = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle < 5 or angle > 175:
                horizontal.append({"y": (y1 + y2) // 2, "x1": x1, "x2": x2, "length": abs(x2 - x1)})

        return horizontal


class VisionController:
    """Main controller orchestrating screen capture and chart analysis."""

    def __init__(self):
        self.screen = ScreenCapture()
        self.pattern_detector = ChartPatternDetector()
        self.image_analyzer = ChartImageAnalyzer()
        self.latest_patterns: list[DetectedPattern] = []
        self.analysis_count: int = 0

    def analyze_ohlc(self, opens, highs, lows, closes) -> list[DetectedPattern]:
        patterns = self.pattern_detector.analyze_candles(
            np.array(opens), np.array(highs), np.array(lows), np.array(closes)
        )
        self.latest_patterns = patterns
        self.analysis_count += 1
        return patterns

    def analyze_chart_screenshot(self, region: tuple = None) -> dict:
        if region:
            x, y, w, h = region
            img = self.screen.capture_region(x, y, w, h)
        else:
            img = self.screen.capture_full_screen()

        if img is None:
            return {"candles": [], "lines": [], "error": "Capture failed"}

        candles = self.image_analyzer.detect_candles_from_image(img)
        lines = self.image_analyzer.detect_horizontal_lines(img)
        self.analysis_count += 1

        return {"candles": candles, "lines": lines, "error": None}

    def get_summary(self) -> dict:
        return {
            "total_analyses": self.analysis_count,
            "latest_pattern_count": len(self.latest_patterns),
            "patterns": [
                {
                    "type": p.pattern_type.value,
                    "confidence": p.confidence,
                    "location": p.location,
                }
                for p in self.latest_patterns
            ],
        }
