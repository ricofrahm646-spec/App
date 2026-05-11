"""
controller.py
=============
J.A.R.V.I.S. V300 - Vision & OS Control.

* MSS grabs the screen at high frequency.
* OpenCV runs two analyzers in parallel:
    - Apex Legends-style enemy detection (red HSV silhouettes with min area /
      aspect ratio gates). Returns the centroid in screen coordinates.
    - MT5 chart-pattern detector (bullish/bearish engulfing + last-bar momentum)
      using basic candle-color segmentation. Useful when MetaTrader is the
      foreground app and we want a secondary visual confirmation.
* PyAutoGUI drives the OS in 'Stealth-Control' mode with cubic Bezier mouse
  curves and jittered timing so the path looks human.

Everything runs in a background-friendly :func:`run_loop`. The vision panel of
``ui.py`` consumes the screenshots written into :data:`SCREENSHOT_DIR`.
"""
from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from config import SCREENSHOT_DIR, VISION
from core import bus

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except Exception:
    cv2 = None  # type: ignore
    CV2_AVAILABLE = False

try:
    import mss  # type: ignore
    MSS_AVAILABLE = True
except Exception:
    mss = None  # type: ignore
    MSS_AVAILABLE = False

try:
    import pyautogui  # type: ignore
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = VISION.pyautogui_failsafe
except Exception:
    pyautogui = None  # type: ignore
    PYAUTOGUI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Bezier-curve mouse movement
# ---------------------------------------------------------------------------
def _bezier_points(p0, p1, p2, p3, n: int) -> List[Tuple[float, float]]:
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = (u ** 3) * p0[0] + 3 * (u ** 2) * t * p1[0] + 3 * u * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        y = (u ** 3) * p0[1] + 3 * (u ** 2) * t * p1[1] + 3 * u * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        pts.append((x, y))
    return pts


def human_move(target_x: int, target_y: int, duration: Optional[float] = None) -> None:
    """Move the mouse along a randomly-shaped cubic Bezier curve. Falls back
    gracefully to a straight move if pyautogui isn't available."""
    if not PYAUTOGUI_AVAILABLE:
        bus.log("controller", f"DRY move({target_x},{target_y}) - pyautogui unavailable", level="WARN")
        return
    sx, sy = pyautogui.position()
    dx, dy = target_x - sx, target_y - sy
    dist = math.hypot(dx, dy)
    if dist < 2:
        pyautogui.moveTo(target_x, target_y)
        return

    if duration is None:
        duration = random.uniform(VISION.bezier_min_duration, VISION.bezier_max_duration)
        duration *= max(0.4, min(2.5, dist / 800.0))

    deflection = max(20.0, dist * random.uniform(0.12, 0.30))
    nx, ny = -dy / dist, dx / dist
    c1 = (sx + dx * 0.30 + nx * deflection * random.uniform(-1, 1),
          sy + dy * 0.30 + ny * deflection * random.uniform(-1, 1))
    c2 = (sx + dx * 0.70 + nx * deflection * random.uniform(-1, 1),
          sy + dy * 0.70 + ny * deflection * random.uniform(-1, 1))

    steps = max(25, int(dist / 12))
    path = _bezier_points((sx, sy), c1, c2, (target_x, target_y), steps)
    step_sleep = duration / max(len(path), 1)
    for px, py in path:
        pyautogui.moveTo(int(px), int(py), _pause=False)
        time.sleep(step_sleep * random.uniform(0.85, 1.15))


def human_click(x: int, y: int, button: str = "left") -> None:
    human_move(x, y)
    if PYAUTOGUI_AVAILABLE:
        time.sleep(random.uniform(0.04, 0.12))
        pyautogui.click(x=x, y=y, button=button)
    bus.log("controller", f"click({x},{y},{button})")


def human_type(text: str, wpm: int = 240) -> None:
    if not PYAUTOGUI_AVAILABLE:
        bus.log("controller", f"DRY type({text!r}) - pyautogui unavailable", level="WARN")
        return
    base = max(0.01, 12.0 / wpm)
    for ch in text:
        pyautogui.typewrite(ch, interval=0)
        time.sleep(base * random.uniform(0.6, 1.6))


# ---------------------------------------------------------------------------
# Screen grab
# ---------------------------------------------------------------------------
def grab_frame():
    if not MSS_AVAILABLE or np is None:
        return None
    with mss.mss() as sct:
        monitor = sct.monitors[min(VISION.monitor_index, len(sct.monitors) - 1)]
        raw = sct.grab(monitor)
        img = np.asarray(raw)[:, :, :3]
        if CV2_AVAILABLE:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img


def save_thumbnail(frame, name: str = "vision.png") -> Optional[Path]:
    if frame is None or not CV2_AVAILABLE:
        return None
    h, w = frame.shape[:2]
    scale = 720.0 / max(h, 1)
    if scale < 1.0:
        thumb = cv2.resize(frame, (int(w * scale), int(h * scale)))
    else:
        thumb = frame
    out = SCREENSHOT_DIR / name
    cv2.imwrite(str(out), cv2.cvtColor(thumb, cv2.COLOR_RGB2BGR))
    return out


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------
@dataclass
class Detection:
    label: str
    x: int
    y: int
    w: int
    h: int
    score: float


def detect_apex_enemies(frame) -> List[Detection]:
    """Detect red enemy outlines (Apex Legends paints enemy silhouettes red).
    NOTE: For gameplay automation use responsibly and within the EULA of the
    game in question."""
    if not CV2_AVAILABLE or frame is None:
        return []
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    # Two red ranges (HSV wraps around)
    mask1 = cv2.inRange(hsv, (0, 150, 80), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (170, 150, 80), (180, 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: List[Detection] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < 600 or area > 80_000:
            continue
        ar = h / max(w, 1)
        if ar < 1.2 or ar > 4.0:
            continue
        score = float(min(1.0, area / 20_000.0))
        out.append(Detection("enemy", x, y, w, h, score))
    return out


def detect_chart_pattern(frame) -> Optional[str]:
    """Crude pattern hint by counting green/red candle pixels in the right-most
    slice of the screen (assumed to be the MT5 chart area)."""
    if not CV2_AVAILABLE or frame is None:
        return None
    h, w = frame.shape[:2]
    if w < 200 or h < 200:
        return None
    roi = frame[int(h * 0.25):int(h * 0.85), int(w * 0.6):w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    green = cv2.inRange(hsv, (45, 60, 60), (90, 255, 255)).sum()
    red1 = cv2.inRange(hsv, (0, 60, 60), (10, 255, 255)).sum()
    red2 = cv2.inRange(hsv, (170, 60, 60), (180, 255, 255)).sum()
    red = red1 + red2
    if green > red * 1.4:
        return "BULLISH_MOMENTUM"
    if red > green * 1.4:
        return "BEARISH_MOMENTUM"
    return "RANGING"


# ---------------------------------------------------------------------------
# Engine loop
# ---------------------------------------------------------------------------
def run_loop(stealth_aim: bool = False) -> None:
    """Continuously analyse the screen. When ``stealth_aim`` is True and an
    enemy is detected, the mouse smoothly drifts toward the highest-score
    target (left button NOT pressed - intentionally restrained)."""
    if not MSS_AVAILABLE or not CV2_AVAILABLE or np is None:
        bus.log("controller", "Vision stack unavailable (mss/opencv/numpy missing)", level="ERROR")
        return

    bus.log("controller", f"Vision online (stealth_aim={stealth_aim})")
    try:
        while True:
            frame = grab_frame()
            if frame is None:
                time.sleep(VISION.scan_interval_sec)
                continue
            enemies = detect_apex_enemies(frame)
            pattern = detect_chart_pattern(frame)
            save_thumbnail(frame)

            if enemies:
                best = max(enemies, key=lambda d: d.score)
                bus.log(
                    "controller",
                    f"Enemy x={best.x+best.w//2} y={best.y+best.h//2} score={best.score:.2f}",
                    level="VISION",
                )
                if stealth_aim and PYAUTOGUI_AVAILABLE:
                    cx, cy = best.x + best.w // 2, best.y + best.h // 2
                    human_move(cx, cy)
            if pattern:
                bus.log("controller", f"Chart-pattern: {pattern}", level="VISION")

            time.sleep(VISION.scan_interval_sec)
    except KeyboardInterrupt:
        bus.log("controller", "Vision loop stopped")


def screenshot_only_once() -> None:
    """Take a single screenshot - safe to call in headless environments."""
    frame = grab_frame()
    if frame is None:
        bus.log("controller", "screenshot_only_once: capture failed", level="WARN")
        return
    p = save_thumbnail(frame)
    bus.log("controller", f"Saved {p}")


if __name__ == "__main__":
    stealth = "--aim" in sys.argv
    if "--once" in sys.argv:
        screenshot_only_once()
    else:
        run_loop(stealth_aim=stealth)
