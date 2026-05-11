from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import mss
except Exception:  # pragma: no cover
    mss = None

try:
    import pyautogui
except Exception:  # pragma: no cover
    pyautogui = None


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScreenVisionController:
    """Computer-vision engine for live screen analysis tasks."""

    def __init__(self, monitor_index: int = 1) -> None:
        self.monitor_index = monitor_index
        self.logs: List[Dict[str, Any]] = []
        self._max_logs = 300

    def log(self, level: str, message: str, **meta: Any) -> None:
        self.logs.append(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "level": level.upper(),
                "message": message,
                "meta": meta,
            }
        )
        self.logs = self.logs[-self._max_logs :]

    def capture_screen(self) -> Optional[np.ndarray]:
        if mss is None:
            self.log("ERROR", "mss package unavailable; screen capture disabled.")
            return None
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                index = min(max(self.monitor_index, 1), len(monitors) - 1)
                frame = np.array(sct.grab(monitors[index]))
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        except Exception as exc:  # pragma: no cover - environment dependent
            self.log("ERROR", "Screen capture failed.", error=str(exc))
            return None

    def detect_apex_enemies(self, frame: np.ndarray) -> List[Detection]:
        """
        Heuristic detector for red/orange highlighted targets in FPS scenes.
        This is a generic CV detector based on color + contour geometry.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        red_low_1 = np.array([0, 110, 70])
        red_high_1 = np.array([12, 255, 255])
        red_low_2 = np.array([160, 110, 70])
        red_high_2 = np.array([179, 255, 255])
        mask = cv2.inRange(hsv, red_low_1, red_high_1) | cv2.inRange(hsv, red_low_2, red_high_2)
        kernel = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        detections: List[Detection] = []
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        frame_area = frame.shape[0] * frame.shape[1]
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 120:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            ratio = w / max(float(h), 1.0)
            if ratio < 0.2 or ratio > 3.0:
                continue
            confidence = min(0.99, (area / max(frame_area, 1)) * 120 + 0.45)
            detections.append(
                Detection(
                    label="apex_enemy_candidate",
                    confidence=float(confidence),
                    bbox=(x, y, w, h),
                    metadata={"area": float(area), "aspect_ratio": ratio},
                )
            )
        detections.sort(key=lambda d: d.confidence, reverse=True)
        self.log("INFO", "Apex detection run complete.", targets=len(detections))
        return detections

    def analyze_mt5_chart(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        MT5 chart scan for trend direction, momentum pressure, and breakout zones.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 60, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=50, maxLineGap=12)

        up_slopes = 0
        down_slopes = 0
        total_lines = 0
        if lines is not None:
            for line in lines[:, 0]:
                x1, y1, x2, y2 = map(int, line)
                if x2 == x1:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                total_lines += 1
                if slope < -0.15:
                    up_slopes += 1
                elif slope > 0.15:
                    down_slopes += 1

        trend = "neutral"
        if up_slopes > down_slopes * 1.2:
            trend = "bullish"
        elif down_slopes > up_slopes * 1.2:
            trend = "bearish"

        hist = cv2.calcHist([gray], [0], None, [16], [0, 256]).flatten()
        hist = hist / max(hist.sum(), 1.0)
        volatility = float(np.std(hist) * 100)

        return {
            "trend": trend,
            "up_slopes": int(up_slopes),
            "down_slopes": int(down_slopes),
            "line_count": int(total_lines),
            "volatility_score": round(volatility, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def annotate(frame: np.ndarray, detections: List[Detection], title: str = "VISION") -> np.ndarray:
        overlay = frame.copy()
        cv2.putText(overlay, title, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 180, 0), 2, cv2.LINE_AA)
        for det in detections:
            x, y, w, h = det.bbox
            color = (50, 220, 255)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                overlay,
                f"{det.label} {det.confidence:.2f}",
                (x, max(15, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )
        return overlay


class StealthControl:
    """Human-like app control using Bezier-mouse trajectories and jitter timing."""

    def __init__(self, fail_safe: bool = True) -> None:
        self.fail_safe = fail_safe
        self.enabled = pyautogui is not None
        if self.enabled:
            pyautogui.FAILSAFE = fail_safe
            pyautogui.PAUSE = 0.0

    @staticmethod
    def _bezier_points(
        start: Tuple[float, float],
        c1: Tuple[float, float],
        c2: Tuple[float, float],
        end: Tuple[float, float],
        steps: int,
    ) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        for i in range(steps + 1):
            t = i / max(steps, 1)
            x = (
                ((1 - t) ** 3) * start[0]
                + 3 * ((1 - t) ** 2) * t * c1[0]
                + 3 * (1 - t) * (t**2) * c2[0]
                + (t**3) * end[0]
            )
            y = (
                ((1 - t) ** 3) * start[1]
                + 3 * ((1 - t) ** 2) * t * c1[1]
                + 3 * (1 - t) * (t**2) * c2[1]
                + (t**3) * end[1]
            )
            points.append((x, y))
        return points

    def move_mouse_humanized(self, x: int, y: int, total_time: Optional[float] = None) -> bool:
        if not self.enabled or pyautogui is None:
            return False
        total_time = total_time or random.uniform(0.25, 0.85)
        start = pyautogui.position()
        end = (x, y)
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.hypot(dx, dy)
        control_spread = max(40.0, distance * 0.33)

        c1 = (
            start[0] + dx * 0.25 + random.uniform(-control_spread, control_spread),
            start[1] + dy * 0.15 + random.uniform(-control_spread, control_spread),
        )
        c2 = (
            start[0] + dx * 0.75 + random.uniform(-control_spread, control_spread),
            start[1] + dy * 0.85 + random.uniform(-control_spread, control_spread),
        )
        steps = int(max(18, min(95, distance / 11)))
        curve = self._bezier_points(start, c1, c2, end, steps)
        sleep_chunk = total_time / max(len(curve), 1)

        for px, py in curve:
            jitter_x = px + random.uniform(-0.6, 0.6)
            jitter_y = py + random.uniform(-0.6, 0.6)
            pyautogui.moveTo(jitter_x, jitter_y, _pause=False)
            time.sleep(max(0.001, sleep_chunk + random.uniform(-0.001, 0.003)))
        return True

    def click_humanized(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        if not self.move_mouse_humanized(x, y):
            return False
        if pyautogui is None:
            return False
        time.sleep(random.uniform(0.04, 0.13))
        pyautogui.click(button=button, clicks=clicks, interval=random.uniform(0.08, 0.22))
        return True

    def locate_and_click(self, image_path: str, confidence: float = 0.8) -> bool:
        if pyautogui is None:
            return False
        try:
            point = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            if point is None:
                return False
            return self.click_humanized(point.x, point.y)
        except Exception:
            return False


def run_vision_cycle(controller: ScreenVisionController) -> Dict[str, Any]:
    frame = controller.capture_screen()
    if frame is None:
        return {"ok": False, "message": "Capture failed"}
    apex = controller.detect_apex_enemies(frame)
    chart = controller.analyze_mt5_chart(frame)
    return {
        "ok": True,
        "apex_targets": [det.__dict__ for det in apex[:10]],
        "chart_analysis": chart,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    vision = ScreenVisionController()
    print(run_vision_cycle(vision))
