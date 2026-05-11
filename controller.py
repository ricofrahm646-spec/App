"""
J.A.R.V.I.S. V300 — VISION & OS CONTROLLER
Screen capture, OCR-based chart analysis, and desktop automation.

NOTE: This module provides screen capture and automation for MT5 chart
      pattern recognition and general desktop control. Game cheating
      features are explicitly excluded.
"""

import io
import math
import random
import time
import threading
from datetime import datetime
from typing import Optional

import numpy as np
from loguru import logger

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available — vision features disabled")

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    logger.warning("MSS not available — screen capture disabled")

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("PyAutoGUI not available — automation disabled")

from config.settings import LOGS_DIR


# ── Bézier Mouse Controller ─────────────────────────────────────────────────

class HumanMouse:
    """Simulates human-like mouse movements using cubic Bézier curves
    with slight randomness for natural feel in desktop automation tasks."""

    @staticmethod
    def bezier_point(t: float, p0: tuple, p1: tuple, p2: tuple, p3: tuple) -> tuple:
        u = 1 - t
        return (
            u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
        )

    @classmethod
    def move_to(cls, x: int, y: int, duration: float = 0.4):
        if not PYAUTOGUI_AVAILABLE:
            logger.debug(f"[SIM] Mouse move to ({x}, {y})")
            return

        start = pyautogui.position()
        p0 = (start[0], start[1])
        p3 = (x, y)

        dx = p3[0] - p0[0]
        dy = p3[1] - p0[1]
        dist = math.hypot(dx, dy)

        spread = max(dist * 0.3, 30)
        p1 = (
            p0[0] + dx * 0.3 + random.uniform(-spread, spread),
            p0[1] + dy * 0.3 + random.uniform(-spread, spread),
        )
        p2 = (
            p0[0] + dx * 0.7 + random.uniform(-spread, spread),
            p0[1] + dy * 0.7 + random.uniform(-spread, spread),
        )

        steps = max(int(dist / 5), 15)
        step_duration = duration / steps

        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)
            bx, by = cls.bezier_point(t, p0, p1, p2, p3)
            bx += random.uniform(-1, 1)
            by += random.uniform(-1, 1)
            pyautogui.moveTo(int(bx), int(by), _pause=False)
            time.sleep(step_duration + random.uniform(-0.005, 0.005))

    @classmethod
    def click_at(cls, x: int, y: int, button: str = "left", duration: float = 0.4):
        cls.move_to(x, y, duration)
        time.sleep(random.uniform(0.03, 0.08))
        if PYAUTOGUI_AVAILABLE:
            pyautogui.click(button=button)
        else:
            logger.debug(f"[SIM] Click {button} at ({x}, {y})")

    @classmethod
    def type_text(cls, text: str, interval: float = 0.05):
        if not PYAUTOGUI_AVAILABLE:
            logger.debug(f"[SIM] Type: {text}")
            return
        for char in text:
            pyautogui.press(char) if len(char) == 1 else pyautogui.press(char)
            time.sleep(interval + random.uniform(-0.02, 0.02))


# ── Screen Capture Engine ────────────────────────────────────────────────────

class ScreenCapture:
    """Captures screen regions using MSS for high-performance frame grabbing."""

    def __init__(self):
        self._sct = None

    def _ensure_sct(self):
        if self._sct is None and MSS_AVAILABLE:
            self._sct = mss.mss()

    def full_screen(self) -> Optional[np.ndarray]:
        if not MSS_AVAILABLE or not CV2_AVAILABLE:
            return self._sim_frame(1920, 1080)

        self._ensure_sct()
        monitor = self._sct.monitors[0]
        img = np.array(self._sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def region(self, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        if not MSS_AVAILABLE or not CV2_AVAILABLE:
            return self._sim_frame(w, h)

        self._ensure_sct()
        monitor = {"top": y, "left": x, "width": w, "height": h}
        img = np.array(self._sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    @staticmethod
    def _sim_frame(w: int, h: int) -> np.ndarray:
        return np.zeros((h, w, 3), dtype=np.uint8)


# ── Chart Pattern Detector ───────────────────────────────────────────────────

class ChartVision:
    """Analyses MT5 chart screenshots for visual pattern recognition."""

    def __init__(self):
        self.capture = ScreenCapture()

    def detect_chart_features(self, frame: np.ndarray) -> dict:
        if not CV2_AVAILABLE:
            return {"candles": 0, "trend_lines": 0, "support_levels": []}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        lines = None
        try:
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                                    minLineLength=50, maxLineGap=10)
        except Exception:
            pass

        horizontal_lines = []
        trend_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(math.atan2(y2 - y1, x2 - x1) * 180 / math.pi)
                if angle < 5 or angle > 175:
                    horizontal_lines.append((min(y1, y2), max(y1, y2)))
                elif 15 < angle < 75 or 105 < angle < 165:
                    trend_lines.append(((x1, y1), (x2, y2)))

        support_levels = self._cluster_horizontal(horizontal_lines)

        green_mask = cv2.inRange(frame, (0, 100, 0), (80, 255, 80))
        red_mask = cv2.inRange(frame, (0, 0, 100), (80, 80, 255))
        green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candle_count = len(green_contours) + len(red_contours)

        return {
            "candles": candle_count,
            "trend_lines": len(trend_lines),
            "support_levels": support_levels,
            "green_candles": len(green_contours),
            "red_candles": len(red_contours),
            "bullish_bias": len(green_contours) > len(red_contours),
        }

    @staticmethod
    def _cluster_horizontal(lines: list, tolerance: int = 10) -> list:
        if not lines:
            return []
        ys = sorted(set(y for y1, y2 in lines for y in (y1, y2)))
        clusters = []
        current_cluster = [ys[0]]
        for y in ys[1:]:
            if y - current_cluster[-1] <= tolerance:
                current_cluster.append(y)
            else:
                clusters.append(int(np.mean(current_cluster)))
                current_cluster = [y]
        if current_cluster:
            clusters.append(int(np.mean(current_cluster)))
        return clusters

    def analyze_mt5_region(self, x: int = 0, y: int = 0,
                           w: int = 1920, h: int = 1080) -> dict:
        frame = self.capture.region(x, y, w, h)
        if frame is None:
            return {}
        return self.detect_chart_features(frame)


# ── Desktop Automation Controller ────────────────────────────────────────────

class DesktopController:
    """High-level desktop automation: window management, app control."""

    def __init__(self):
        self.mouse = HumanMouse()

    def find_window(self, title: str) -> Optional[tuple]:
        if not PYAUTOGUI_AVAILABLE:
            logger.debug(f"[SIM] Find window: {title}")
            return (0, 0, 1920, 1080)

        try:
            windows = pyautogui.getWindowsWithTitle(title)
            if windows:
                w = windows[0]
                return (w.left, w.top, w.width, w.height)
        except Exception as e:
            logger.debug(f"Window search failed: {e}")
        return None

    def focus_window(self, title: str) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            logger.debug(f"[SIM] Focus window: {title}")
            return True

        try:
            windows = pyautogui.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                time.sleep(0.3)
                return True
        except Exception as e:
            logger.debug(f"Focus failed: {e}")
        return False

    def screenshot_region(self, x: int, y: int, w: int, h: int,
                          save_path: Optional[str] = None) -> Optional[np.ndarray]:
        capture = ScreenCapture()
        frame = capture.region(x, y, w, h)
        if frame is not None and save_path and CV2_AVAILABLE:
            cv2.imwrite(save_path, frame)
        return frame

    def press_key(self, key: str):
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press(key)
        else:
            logger.debug(f"[SIM] Key press: {key}")

    def hotkey(self, *keys):
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey(*keys)
        else:
            logger.debug(f"[SIM] Hotkey: {'+'.join(keys)}")


# ── Vision Controller (Orchestrator) ─────────────────────────────────────────

class VisionController:
    """Main controller that ties screen capture, chart vision, and automation."""

    def __init__(self):
        self.chart_vision = ChartVision()
        self.desktop = DesktopController()
        self.running = False
        self.fps = 0
        self.detections = 0
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("VisionController started — monitoring active")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("VisionController stopped")

    def _loop(self):
        frame_count = 0
        start_time = time.time()

        while self.running:
            try:
                features = self.chart_vision.analyze_mt5_region()
                if features:
                    self.detections = features.get("candles", 0)
                    frame_count += 1

                elapsed = time.time() - start_time
                if elapsed >= 1.0:
                    self.fps = frame_count / elapsed
                    frame_count = 0
                    start_time = time.time()

                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Vision loop error: {e}")
                time.sleep(1)

    def get_status(self) -> dict:
        return {
            "status": "ACTIVE" if self.running else "STANDBY",
            "fps": round(self.fps, 1),
            "detections": self.detections,
        }


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.add(LOGS_DIR / "controller.log", rotation="10 MB", retention="7 days")

    vc = VisionController()
    vc.start()

    try:
        while True:
            status = vc.get_status()
            logger.info(f"Vision Status: {status}")
            time.sleep(5)
    except KeyboardInterrupt:
        vc.stop()
        logger.info("Sir, vision controller shut down.")
