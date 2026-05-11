"""Vision and assistive OS control for JARVIS V300.

The controller provides screen capture, chart/attention-region analysis, and
human-like input automation for approved desktop workflows. It deliberately
blocks game automation and covert control. This keeps the module useful for
accessibility, QA, and trading-dashboard workflows without enabling cheating or
unconsented interaction with protected applications.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - optional native dependency
    cv2 = None  # type: ignore[assignment]

try:
    import mss
except Exception:  # pragma: no cover - optional native dependency
    mss = None  # type: ignore[assignment]

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore[assignment]

try:
    import pyautogui
except Exception:  # pragma: no cover - may fail on headless systems
    pyautogui = None  # type: ignore[assignment]

try:
    import pygetwindow
except Exception:  # pragma: no cover - optional window title dependency
    pygetwindow = None  # type: ignore[assignment]


LOGGER = logging.getLogger("jarvis.controller")
CONTROL_LOG = Path("logs/controller.jsonl")
BLOCKED_APP_TERMS = {
    "apex",
    "r5apex",
    "easyanticheat",
    "valorant",
    "counter-strike",
    "fortnite",
}


@dataclass(frozen=True)
class Detection:
    kind: str
    confidence: float
    bbox: tuple[int, int, int, int]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChartPattern:
    kind: str
    confidence: float
    description: str
    points: tuple[tuple[int, int], ...] = ()


@dataclass
class ControllerConfig:
    enable_os_control: bool = os.getenv("JARVIS_ENABLE_OS_CONTROL", "0") == "1"
    dry_run: bool = os.getenv("JARVIS_CONTROL_DRY_RUN", "1") != "0"
    max_mouse_duration: float = 1.4
    min_mouse_duration: float = 0.18
    log_path: Path = CONTROL_LOG
    allowed_window_terms: tuple[str, ...] = ("metatrader", "streamlit", "terminal", "browser", "code")


class ScreenAnalyzer:
    def __init__(self) -> None:
        self._last_frame: np.ndarray | None = None

    def capture(self, monitor: int = 1) -> np.ndarray:
        if mss is None:
            raise RuntimeError("mss is not installed; screen capture is unavailable.")
        with mss.mss() as grabber:
            monitors = grabber.monitors
            selected = monitors[monitor] if monitor < len(monitors) else monitors[0]
            raw = np.array(grabber.grab(selected))
        frame = raw[:, :, :3]
        if cv2 is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def analyze_screen(self, frame: np.ndarray | None = None) -> dict[str, Any]:
        frame = frame if frame is not None else self.capture()
        detections = self.detect_attention_regions(frame)
        chart_patterns = self.detect_chart_patterns(frame)
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "shape": tuple(int(v) for v in frame.shape),
            "attention_regions": [asdict(item) for item in detections],
            "chart_patterns": [asdict(item) for item in chart_patterns],
        }
        self._last_frame = frame.copy()
        return result

    def detect_attention_regions(self, frame: np.ndarray) -> list[Detection]:
        """Detect salient non-game screen regions using color, contrast, and motion."""
        if cv2 is None:
            return []
        resized = self._resize_for_analysis(frame)
        hsv = cv2.cvtColor(resized, cv2.COLOR_RGB2HSV)
        saturation_mask = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([179, 255, 255]))
        gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 70, 160)
        combined = cv2.bitwise_or(saturation_mask, edges)

        if self._last_frame is not None:
            last = self._resize_for_analysis(self._last_frame)
            diff = cv2.absdiff(cv2.cvtColor(last, cv2.COLOR_RGB2GRAY), gray)
            _, motion = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)
            combined = cv2.bitwise_or(combined, motion)

        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: list[Detection] = []
        scale_x = frame.shape[1] / resized.shape[1]
        scale_y = frame.shape[0] / resized.shape[0]
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 180 or area > resized.shape[0] * resized.shape[1] * 0.20:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            confidence = min(0.98, 0.30 + (area / 6000.0))
            detections.append(
                Detection(
                    kind="attention_region",
                    confidence=round(float(confidence), 3),
                    bbox=(
                        int(x * scale_x),
                        int(y * scale_y),
                        int(w * scale_x),
                        int(h * scale_y),
                    ),
                    metadata={"area": round(float(area), 2)},
                )
            )
        return sorted(detections, key=lambda item: item.confidence, reverse=True)[:12]

    def detect_chart_patterns(self, frame: np.ndarray) -> list[ChartPattern]:
        if cv2 is None:
            return []
        resized = self._resize_for_analysis(frame, width=900)
        gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 45, 130)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=70, minLineLength=70, maxLineGap=15)
        if lines is None:
            return []

        slopes: list[float] = []
        points: list[tuple[int, int]] = []
        for line in lines[:80]:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            slope = (y2 - y1) / (x2 - x1)
            if abs(slope) < 0.02:
                slopes.append(0.0)
            elif abs(slope) < 1.2:
                slopes.append(float(slope))
                points.extend([(int(x1), int(y1)), (int(x2), int(y2))])

        patterns: list[ChartPattern] = []
        horizontal_count = sum(1 for slope in slopes if slope == 0.0)
        rising = sum(1 for slope in slopes if slope < -0.10)
        falling = sum(1 for slope in slopes if slope > 0.10)
        if horizontal_count >= 4:
            patterns.append(
                ChartPattern(
                    "support_resistance_cluster",
                    min(0.95, 0.45 + horizontal_count / 20),
                    "Multiple horizontal reactions detected; inspect for liquidity pools.",
                )
            )
        if rising >= 3:
            patterns.append(
                ChartPattern(
                    "ascending_structure",
                    min(0.92, 0.42 + rising / 18),
                    "Rising diagonal structure detected in chart region.",
                    tuple(points[:8]),
                )
            )
        if falling >= 3:
            patterns.append(
                ChartPattern(
                    "descending_structure",
                    min(0.92, 0.42 + falling / 18),
                    "Falling diagonal structure detected in chart region.",
                    tuple(points[:8]),
                )
            )
        return patterns

    @staticmethod
    def _resize_for_analysis(frame: np.ndarray, width: int = 640) -> np.ndarray:
        if cv2 is None or frame.shape[1] <= width:
            return frame
        ratio = width / frame.shape[1]
        height = max(1, int(frame.shape[0] * ratio))
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)


class OSController:
    def __init__(self, config: ControllerConfig | None = None) -> None:
        self.config = config or ControllerConfig()
        self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
        if pyautogui is not None:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.04

    def active_window_title(self) -> str:
        if pygetwindow is None:
            return ""
        try:
            window = pygetwindow.getActiveWindow()
            return str(window.title if window else "")
        except Exception:
            return ""

    def safe_to_control(self) -> tuple[bool, str]:
        if not self.config.enable_os_control:
            return False, "OS control disabled; set JARVIS_ENABLE_OS_CONTROL=1 to enable."
        if pyautogui is None:
            return False, "pyautogui is unavailable."
        if self._blocked_process_running():
            return False, "blocked game or anti-cheat process detected."
        title = self.active_window_title().lower()
        if title and any(term in title for term in BLOCKED_APP_TERMS):
            return False, f"blocked active window: {title}"
        if title and not any(term in title for term in self.config.allowed_window_terms):
            return False, f"active window is not allowlisted: {title}"
        return True, "ok"

    def move_mouse(self, x: int, y: int, duration: float | None = None) -> dict[str, Any]:
        allowed, reason = self.safe_to_control()
        action = {"action": "move_mouse", "x": x, "y": y, "allowed": allowed, "reason": reason}
        if not allowed or self.config.dry_run:
            self._log(action | {"dry_run": self.config.dry_run})
            return action | {"status": "dry_run" if self.config.dry_run else "blocked"}
        duration = duration or random.uniform(self.config.min_mouse_duration, self.config.max_mouse_duration)
        for px, py in self._bezier_path_to(x, y, duration):
            pyautogui.moveTo(px, py, duration=0)
            time.sleep(max(0.003, duration / 90))
        self._log(action | {"duration": duration, "status": "done"})
        return action | {"status": "done"}

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> dict[str, Any]:
        allowed, reason = self.safe_to_control()
        action = {"action": "click", "x": x, "y": y, "button": button, "allowed": allowed, "reason": reason}
        if not allowed or self.config.dry_run:
            self._log(action | {"dry_run": self.config.dry_run})
            return action | {"status": "dry_run" if self.config.dry_run else "blocked"}
        if x is not None and y is not None:
            self.move_mouse(x, y)
        pyautogui.click(button=button)
        self._log(action | {"status": "done"})
        return action | {"status": "done"}

    def type_text(self, text: str, interval: float = 0.02) -> dict[str, Any]:
        allowed, reason = self.safe_to_control()
        action = {"action": "type_text", "length": len(text), "allowed": allowed, "reason": reason}
        if not allowed or self.config.dry_run:
            self._log(action | {"dry_run": self.config.dry_run})
            return action | {"status": "dry_run" if self.config.dry_run else "blocked"}
        pyautogui.write(text, interval=interval)
        self._log(action | {"status": "done"})
        return action | {"status": "done"}

    def hotkey(self, *keys: str) -> dict[str, Any]:
        allowed, reason = self.safe_to_control()
        action = {"action": "hotkey", "keys": keys, "allowed": allowed, "reason": reason}
        if not allowed or self.config.dry_run:
            self._log(action | {"dry_run": self.config.dry_run})
            return action | {"status": "dry_run" if self.config.dry_run else "blocked"}
        pyautogui.hotkey(*keys)
        self._log(action | {"status": "done"})
        return action | {"status": "done"}

    def _bezier_path_to(self, x: int, y: int, duration: float) -> list[tuple[int, int]]:
        if pyautogui is None:
            return [(x, y)]
        start_x, start_y = pyautogui.position()
        steps = max(12, min(110, int(duration * 75)))
        ctrl1 = (
            start_x + (x - start_x) * random.uniform(0.20, 0.40) + random.uniform(-70, 70),
            start_y + (y - start_y) * random.uniform(0.20, 0.40) + random.uniform(-70, 70),
        )
        ctrl2 = (
            start_x + (x - start_x) * random.uniform(0.60, 0.85) + random.uniform(-70, 70),
            start_y + (y - start_y) * random.uniform(0.60, 0.85) + random.uniform(-70, 70),
        )
        path: list[tuple[int, int]] = []
        for idx in range(steps + 1):
            t = idx / steps
            eased = 0.5 - 0.5 * math.cos(math.pi * t)
            bx = (
                (1 - eased) ** 3 * start_x
                + 3 * (1 - eased) ** 2 * eased * ctrl1[0]
                + 3 * (1 - eased) * eased**2 * ctrl2[0]
                + eased**3 * x
            )
            by = (
                (1 - eased) ** 3 * start_y
                + 3 * (1 - eased) ** 2 * eased * ctrl1[1]
                + 3 * (1 - eased) * eased**2 * ctrl2[1]
                + eased**3 * y
            )
            path.append((int(round(bx)), int(round(by))))
        return path

    def _blocked_process_running(self) -> bool:
        if psutil is None:
            return False
        for proc in psutil.process_iter(["name"]):
            try:
                name = str(proc.info.get("name", "")).lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if any(term in name for term in BLOCKED_APP_TERMS):
                return True
        return False

    def _log(self, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str, sort_keys=True) + "\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")
    analyzer = ScreenAnalyzer()
    controller = OSController()
    try:
        analysis = analyzer.analyze_screen()
    except Exception as exc:
        analysis = {"status": "capture_unavailable", "reason": str(exc)}
    print(json.dumps({"analysis": analysis, "control_state": controller.safe_to_control()}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
