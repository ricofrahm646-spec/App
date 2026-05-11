from __future__ import annotations

import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

try:
    import mss
except Exception:  # pragma: no cover - optional at runtime
    mss = None

try:
    import pyautogui
except Exception:  # pragma: no cover - optional at runtime
    pyautogui = None


@dataclass(slots=True)
class ScreenMatch:
    x: int
    y: int
    width: int
    height: int
    confidence: float
    label: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class VisionReport:
    resolution: tuple[int, int]
    chart_pattern: str
    trend_bias: str
    contour_count: int
    template_matches: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


class ScreenVision:
    def capture(self, monitor_index: int = 1) -> np.ndarray:
        if mss is None:
            raise RuntimeError("mss is not installed")
        with mss.mss() as sct:
            monitor = sct.monitors[min(monitor_index, len(sct.monitors) - 1)]
            shot = np.array(sct.grab(monitor))
        return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)

    @staticmethod
    def detect_template(frame: np.ndarray, template_path: str | Path, threshold: float = 0.84) -> list[ScreenMatch]:
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise FileNotFoundError(template_path)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        y_indices, x_indices = np.where(result >= threshold)
        matches: list[ScreenMatch] = []
        for x, y in zip(x_indices, y_indices):
            matches.append(
                ScreenMatch(
                    x=int(x),
                    y=int(y),
                    width=int(template.shape[1]),
                    height=int(template.shape[0]),
                    confidence=float(result[y, x]),
                    label=Path(template_path).stem,
                )
            )
        return matches

    @staticmethod
    def extract_price_trace(frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        height, width = edges.shape
        trace = np.zeros(width, dtype=float)
        for x in range(width):
            bright_pixels = np.where(edges[:, x] > 0)[0]
            trace[x] = float(height - np.median(bright_pixels)) if bright_pixels.size else trace[x - 1] if x else height / 2
        return trace

    @staticmethod
    def classify_chart_pattern(trace: np.ndarray) -> tuple[str, str]:
        if trace.size < 20:
            return "insufficient-data", "neutral"

        smooth = np.convolve(trace, np.ones(9) / 9, mode="same")
        slope = float(np.polyfit(np.arange(smooth.size), smooth, 1)[0])
        trend_bias = "bullish" if slope > 0.05 else "bearish" if slope < -0.05 else "sideways"

        peaks = []
        troughs = []
        for idx in range(2, len(smooth) - 2):
            window = smooth[idx - 2 : idx + 3]
            if smooth[idx] == np.max(window):
                peaks.append((idx, smooth[idx]))
            if smooth[idx] == np.min(window):
                troughs.append((idx, smooth[idx]))

        if len(peaks) >= 2 and abs(peaks[-1][1] - peaks[-2][1]) < np.std(smooth) * 0.3:
            return "double-top", trend_bias
        if len(troughs) >= 2 and abs(troughs[-1][1] - troughs[-2][1]) < np.std(smooth) * 0.3:
            return "double-bottom", trend_bias
        if abs(slope) < 0.03:
            return "range-compression", trend_bias
        return "trend-expansion", trend_bias

    def analyze_chart(self, frame: np.ndarray, templates: Optional[list[str]] = None) -> VisionReport:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        trace = self.extract_price_trace(frame)
        pattern, bias = self.classify_chart_pattern(trace)

        matches: list[dict] = []
        for template_path in templates or []:
            for match in self.detect_template(frame, template_path):
                matches.append(match.to_dict())

        return VisionReport(
            resolution=(int(frame.shape[1]), int(frame.shape[0])),
            chart_pattern=pattern,
            trend_bias=bias,
            contour_count=len(contours),
            template_matches=matches,
        )


class BezierMouse:
    @staticmethod
    def generate_curve(start: tuple[int, int], end: tuple[int, int], steps: int = 32) -> list[tuple[int, int]]:
        distance = math.dist(start, end)
        arc = max(40.0, distance * 0.15)
        ctrl_1 = (start[0] + (end[0] - start[0]) * 0.25, start[1] - arc)
        ctrl_2 = (start[0] + (end[0] - start[0]) * 0.75, end[1] + arc * 0.45)
        points: list[tuple[int, int]] = []

        for step in range(steps + 1):
            t = step / steps
            omt = 1 - t
            x = (
                omt**3 * start[0]
                + 3 * omt**2 * t * ctrl_1[0]
                + 3 * omt * t**2 * ctrl_2[0]
                + t**3 * end[0]
            )
            y = (
                omt**3 * start[1]
                + 3 * omt**2 * t * ctrl_1[1]
                + 3 * omt * t**2 * ctrl_2[1]
                + t**3 * end[1]
            )
            points.append((int(round(x)), int(round(y))))
        return points


class DesktopController:
    def __init__(self, allow_control: bool | None = None) -> None:
        env_flag = os.getenv("JARVIS_ALLOW_DESKTOP_CONTROL", "0") == "1"
        self.allow_control = env_flag if allow_control is None else allow_control

    def move_mouse_humanized(self, target: tuple[int, int], duration: float = 0.7) -> list[tuple[int, int]]:
        if pyautogui is None:
            raise RuntimeError("pyautogui is not installed")

        pyautogui.FAILSAFE = True
        start = tuple(map(int, pyautogui.position()))
        curve = BezierMouse.generate_curve(start=start, end=target)
        if not self.allow_control:
            return curve

        step_delay = max(duration / max(len(curve), 1), 0.01)
        for point in curve:
            pyautogui.moveTo(point[0], point[1], duration=0)
            time.sleep(step_delay)
        return curve

    def click(self, target: tuple[int, int], button: str = "left") -> None:
        if not self.allow_control:
            raise PermissionError("Desktop control is disabled. Set JARVIS_ALLOW_DESKTOP_CONTROL=1 to enable.")
        if pyautogui is None:
            raise RuntimeError("pyautogui is not installed")
        self.move_mouse_humanized(target)
        pyautogui.click(button=button)


if __name__ == "__main__":
    vision = ScreenVision()
    if mss is not None:
        frame = vision.capture()
        print(vision.analyze_chart(frame).to_dict())
