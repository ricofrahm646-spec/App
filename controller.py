from __future__ import annotations

import json
import logging
import math
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:
    import mss
except Exception:  # pragma: no cover - optional dependency
    mss = None

try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
SCREEN_STATE_FILE = RUNTIME_DIR / "screen_snapshot.json"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("jarvis.controller")


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenReport:
    captured_at: str
    source: str
    detections: list[Detection]
    summary: dict[str, Any]
    image_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "source": self.source,
            "detections": [asdict(item) for item in self.detections],
            "summary": self.summary,
            "image_path": self.image_path,
        }


class ScreenVision:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or (RUNTIME_DIR / "captures")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _synthetic_frame(self) -> np.ndarray:
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        for idx in range(20, 1260, 45):
            height = int(360 + math.sin(idx / 60) * 130)
            frame[height : height + 3, idx - 12 : idx + 12] = (255, 120, 0)
            frame[height - 35 : height + 35, idx : idx + 2] = (0, 200, 255)
        return frame

    def capture(self, monitor: int = 1, region: dict[str, int] | None = None) -> tuple[np.ndarray, str]:
        if mss is None:
            return self._synthetic_frame(), "synthetic"

        with mss.mss() as sct:
            target = region or sct.monitors[min(monitor, len(sct.monitors) - 1)]
            shot = np.array(sct.grab(target))
            return shot[:, :, :3], "live"

    def _template_match(
        self, frame: np.ndarray, template_path: str | None, threshold: float = 0.82
    ) -> list[Detection]:
        if cv2 is None or not template_path or not Path(template_path).exists():
            return []
        template = cv2.imread(str(template_path))
        if template is None:
            return []
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        y_coords, x_coords = np.where(result >= threshold)
        detections: list[Detection] = []
        for x_coord, y_coord in zip(x_coords[:12], y_coords[:12]):
            detections.append(
                Detection(
                    label="template_match",
                    confidence=float(result[y_coord, x_coord]),
                    bbox=(int(x_coord), int(y_coord), int(template.shape[1]), int(template.shape[0])),
                )
            )
        return detections

    def detect_chart_features(self, frame: np.ndarray) -> list[Detection]:
        if cv2 is None:
            return [Detection(label="opencv_unavailable", confidence=0.0)]

        detections: list[Detection] = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 120)

        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=50, maxLineGap=20)
        horizontal = 0
        diagonal = 0
        if lines is not None:
            for line in lines[:300]:
                x1, y1, x2, y2 = line[0]
                if abs(y1 - y2) <= 4:
                    horizontal += 1
                if abs(x1 - x2) > 10 and abs(y1 - y2) > 10:
                    diagonal += 1

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bright_masks = cv2.inRange(frame, (160, 160, 160), (255, 255, 255))
        bright_count = int(cv2.connectedComponents(bright_masks)[0]) - 1

        if horizontal >= 8:
            detections.append(
                Detection("support_resistance_cluster", min(horizontal / 25, 0.99), meta={"count": horizontal})
            )
        if diagonal >= 6:
            detections.append(
                Detection("momentum_channel", min(diagonal / 20, 0.99), meta={"count": diagonal})
            )

        rectangular_zones = 0
        for contour in contours[:200]:
            x_pos, y_pos, width, height = cv2.boundingRect(contour)
            area = width * height
            if area > 1200 and 0.7 <= width / max(height, 1) <= 4.0:
                rectangular_zones += 1
        if rectangular_zones:
            detections.append(
                Detection(
                    "imbalance_zone_cluster",
                    min(rectangular_zones / 12, 0.99),
                    meta={"count": rectangular_zones},
                )
            )

        if bright_count >= 10:
            detections.append(
                Detection("ui_hotspots", min(bright_count / 30, 0.99), meta={"count": bright_count})
            )

        return detections

    def save_annotated_frame(self, frame: np.ndarray, detections: list[Detection]) -> str | None:
        if cv2 is None:
            return None
        annotated = frame.copy()
        for detection in detections:
            if detection.bbox:
                x_pos, y_pos, width, height = detection.bbox
                cv2.rectangle(annotated, (x_pos, y_pos), (x_pos + width, y_pos + height), (255, 150, 0), 2)
                cv2.putText(
                    annotated,
                    f"{detection.label}:{detection.confidence:.2f}",
                    (x_pos, max(y_pos - 10, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (30, 220, 255),
                    1,
                    cv2.LINE_AA,
                )
        output_path = self.output_dir / f"capture_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(str(output_path), annotated)
        return str(output_path)

    def analyze(self, region: dict[str, int] | None = None, template_path: str | None = None) -> ScreenReport:
        frame, source = self.capture(region=region)
        detections = self.detect_chart_features(frame)
        detections.extend(self._template_match(frame, template_path))
        summary = {
            "detection_count": len(detections),
            "labels": [item.label for item in detections],
            "resolution": {"height": int(frame.shape[0]), "width": int(frame.shape[1])},
        }
        image_path = self.save_annotated_frame(frame, detections)
        report = ScreenReport(
            captured_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            detections=detections,
            summary=summary,
            image_path=image_path,
        )
        SCREEN_STATE_FILE.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return report


class HumanCursor:
    def __init__(self) -> None:
        if pyautogui is not None:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.01

    def _position(self) -> tuple[int, int]:
        if pyautogui is None:
            return (0, 0)
        return pyautogui.position()

    def _bezier_points(
        self, start: tuple[int, int], end: tuple[int, int], steps: int = 60
    ) -> list[tuple[int, int]]:
        control_1 = (
            int(start[0] + (end[0] - start[0]) * 0.3 + random.randint(-80, 80)),
            int(start[1] + random.randint(-100, 100)),
        )
        control_2 = (
            int(start[0] + (end[0] - start[0]) * 0.7 + random.randint(-80, 80)),
            int(end[1] + random.randint(-100, 100)),
        )
        points: list[tuple[int, int]] = []
        for index in range(steps + 1):
            t = index / steps
            x_pos = (
                ((1 - t) ** 3) * start[0]
                + 3 * ((1 - t) ** 2) * t * control_1[0]
                + 3 * (1 - t) * (t**2) * control_2[0]
                + (t**3) * end[0]
            )
            y_pos = (
                ((1 - t) ** 3) * start[1]
                + 3 * ((1 - t) ** 2) * t * control_1[1]
                + 3 * (1 - t) * (t**2) * control_2[1]
                + (t**3) * end[1]
            )
            points.append((int(x_pos), int(y_pos)))
        return points

    def move_to(self, x_pos: int, y_pos: int, duration: float = 0.8) -> bool:
        if pyautogui is None:
            return False
        start = self._position()
        points = self._bezier_points(start, (x_pos, y_pos))
        interval = max(duration / max(len(points), 1), 0.002)
        for point in points:
            pyautogui.moveTo(point[0], point[1], duration=0)
            time.sleep(interval + random.uniform(0.0, 0.002))
        return True

    def click(self, x_pos: int, y_pos: int, button: str = "left") -> bool:
        if not self.move_to(x_pos, y_pos):
            return False
        pyautogui.click(button=button)
        return True

    def drag_to(self, x_pos: int, y_pos: int, duration: float = 1.2) -> bool:
        if pyautogui is None:
            return False
        start = self._position()
        points = self._bezier_points(start, (x_pos, y_pos), steps=90)
        pyautogui.mouseDown()
        try:
            interval = max(duration / max(len(points), 1), 0.002)
            for point in points:
                pyautogui.moveTo(point[0], point[1], duration=0)
                time.sleep(interval)
        finally:
            pyautogui.mouseUp()
        return True

    def type_text(self, text: str, interval: float = 0.035) -> bool:
        if pyautogui is None:
            return False
        pyautogui.write(text, interval=interval)
        return True


class DesktopController:
    def __init__(self) -> None:
        self.vision = ScreenVision()
        self.cursor = HumanCursor()

    def analyze_market_screen(
        self, region: dict[str, int] | None = None, template_path: str | None = None
    ) -> dict[str, Any]:
        report = self.vision.analyze(region=region, template_path=template_path)
        return report.to_dict()

    def click_point(self, x_pos: int, y_pos: int) -> bool:
        return self.cursor.click(x_pos, y_pos)

    def drag_point(self, x_pos: int, y_pos: int) -> bool:
        return self.cursor.drag_to(x_pos, y_pos)

    def type_text(self, text: str) -> bool:
        return self.cursor.type_text(text)


def main() -> None:
    controller = DesktopController()
    report = controller.analyze_market_screen()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
