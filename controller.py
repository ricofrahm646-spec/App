"""
VISION & OS-CONTROL
-------------------

Computer-vision screen analysis and explicit opt-in desktop automation.

This module captures screenshots, extracts MT5 chart features, and provides a
human-like mouse movement primitive for legitimate desktop workflows. It refuses
to automate competitive games or hidden user actions.
"""

from __future__ import annotations

import logging
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Any

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional native dependency
    cv2 = None  # type: ignore

try:
    import mss  # type: ignore
except Exception:  # pragma: no cover
    mss = None  # type: ignore

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover
    pyautogui = None  # type: ignore


LOG = logging.getLogger("controller")

BLOCKED_APP_HINTS = {"apex legends", "valorant", "fortnite", "counter-strike", "warzone"}


@dataclass(frozen=True)
class ScreenTarget:
    label: str
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


@dataclass(frozen=True)
class ChartPattern:
    name: str
    confidence: float
    details: dict[str, float]


class ScreenVision:
    def __init__(self, monitor_index: int = 1) -> None:
        self.monitor_index = monitor_index

    def capture(self) -> Any:
        if mss is None or np is None:
            raise RuntimeError("mss and numpy are required for screen capture")
        with mss.mss() as session:
            monitors = session.monitors
            index = self.monitor_index if self.monitor_index < len(monitors) else 0
            shot = session.grab(monitors[index])
        return np.array(shot)

    def detect_mt5_chart_patterns(self, image: Any | None = None) -> list[ChartPattern]:
        if cv2 is None or np is None:
            raise RuntimeError("opencv-python and numpy are required for chart analysis")
        frame = image if image is not None else self.capture()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY) if frame.shape[-1] == 4 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, math.pi / 180, threshold=80, minLineLength=45, maxLineGap=10)
        if lines is None:
            return []

        slopes: list[float] = []
        for line in lines[:, 0, :]:
            x1, y1, x2, y2 = [int(value) for value in line]
            if x2 == x1:
                continue
            slopes.append((y2 - y1) / (x2 - x1))
        if not slopes:
            return []

        positive = [s for s in slopes if s > 0.15]
        negative = [s for s in slopes if s < -0.15]
        horizontal = [s for s in slopes if abs(s) <= 0.08]
        total = max(1, len(slopes))
        patterns: list[ChartPattern] = []
        if len(horizontal) / total > 0.35:
            patterns.append(
                ChartPattern(
                    "liquidity_range",
                    min(0.95, len(horizontal) / total + 0.35),
                    {"horizontal_ratio": len(horizontal) / total},
                )
            )
        if positive and negative:
            balance = 1 - abs(len(positive) - len(negative)) / max(len(positive), len(negative))
            if balance > 0.45:
                patterns.append(
                    ChartPattern(
                        "compression_triangle",
                        min(0.92, balance),
                        {"positive_lines": float(len(positive)), "negative_lines": float(len(negative))},
                    )
                )
        if len(positive) / total > 0.45:
            patterns.append(
                ChartPattern("rising_channel", min(0.9, len(positive) / total + 0.25), {"slope_count": float(len(positive))})
            )
        if len(negative) / total > 0.45:
            patterns.append(
                ChartPattern("falling_channel", min(0.9, len(negative) / total + 0.25), {"slope_count": float(len(negative))})
            )
        return sorted(patterns, key=lambda item: item.confidence, reverse=True)

    def detect_visual_alerts(self, image: Any | None = None) -> list[ScreenTarget]:
        """Detect high-saturation red UI markers for operator awareness.

        The method is intentionally generic and returns targets for display or
        logging only. It is not wired to aim, fire, or manipulate games.
        """

        if cv2 is None or np is None:
            raise RuntimeError("opencv-python and numpy are required for visual alert detection")
        frame = image if image is not None else self.capture()
        bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR) if frame.shape[-1] == 4 else frame
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lower_red_a = np.array([0, 120, 110])
        upper_red_a = np.array([10, 255, 255])
        lower_red_b = np.array([170, 120, 110])
        upper_red_b = np.array([180, 255, 255])
        mask = cv2.inRange(hsv, lower_red_a, upper_red_a) | cv2.inRange(hsv, lower_red_b, upper_red_b)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        targets: list[ScreenTarget] = []
        screen_area = frame.shape[0] * frame.shape[1]
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 40 or area > screen_area * 0.15:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            confidence = min(0.99, area / max(1, w * h))
            targets.append(ScreenTarget("red_visual_alert", x, y, w, h, confidence))
        return sorted(targets, key=lambda target: target.confidence, reverse=True)


class DesktopController:
    def __init__(self, allow_control: bool | None = None) -> None:
        self.allow_control = (
            os.getenv("JARVIS_OS_CONTROL", "").lower() in {"1", "true", "yes"}
            if allow_control is None
            else allow_control
        )
        if pyautogui is not None:
            pyautogui.FAILSAFE = True

    def _assert_allowed(self, app_title: str | None = None) -> None:
        if not self.allow_control:
            raise PermissionError("Desktop control requires JARVIS_OS_CONTROL=1 or allow_control=True")
        title = (app_title or "").lower()
        if any(hint in title for hint in BLOCKED_APP_HINTS):
            raise PermissionError(f"Automation is blocked for competitive game window: {app_title}")
        if pyautogui is None:
            raise RuntimeError("pyautogui is required for desktop control")

    def bezier_move_to(
        self,
        x: int,
        y: int,
        duration: float = 0.65,
        app_title: str | None = None,
    ) -> None:
        self._assert_allowed(app_title)
        start_x, start_y = pyautogui.position()
        control_1 = (
            start_x + random.randint(-120, 120),
            start_y + random.randint(40, 180),
        )
        control_2 = (
            x + random.randint(-120, 120),
            y + random.randint(-180, -40),
        )
        steps = max(12, int(duration * 60))
        for step in range(steps + 1):
            t = step / steps
            bx = self._cubic_bezier(start_x, control_1[0], control_2[0], x, t)
            by = self._cubic_bezier(start_y, control_1[1], control_2[1], y, t)
            pyautogui.moveTo(bx, by)
            time.sleep(duration / steps)

    def click_target(self, target: ScreenTarget, app_title: str | None = None) -> None:
        x, y = target.center
        self.bezier_move_to(x, y, app_title=app_title)
        pyautogui.click()

    def type_text(self, text: str, interval: float = 0.025, app_title: str | None = None) -> None:
        self._assert_allowed(app_title)
        pyautogui.write(text, interval=interval)

    @staticmethod
    def _cubic_bezier(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
        return (
            ((1 - t) ** 3) * p0
            + 3 * ((1 - t) ** 2) * t * p1
            + 3 * (1 - t) * (t**2) * p2
            + (t**3) * p3
        )


class VisionController:
    def __init__(self, allow_control: bool | None = None) -> None:
        self.vision = ScreenVision()
        self.desktop = DesktopController(allow_control=allow_control)

    def analyze_screen(self) -> dict[str, Any]:
        frame = self.vision.capture()
        patterns = self.vision.detect_mt5_chart_patterns(frame)
        alerts = self.vision.detect_visual_alerts(frame)
        return {"chart_patterns": patterns, "visual_alerts": alerts[:10]}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    controller = VisionController()
    print(controller.analyze_screen())
