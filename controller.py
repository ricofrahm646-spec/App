"""
Screen capture (MSS) + OpenCV analysis and human-like pointer paths (Bézier).
Use only on systems and applications you own or are authorized to automate.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from scipy.special import comb

try:
    import mss
    import mss.tools
except ImportError:
    mss = None  # type: ignore

try:
    import pyautogui
except ImportError:
    pyautogui = None  # type: ignore

log = logging.getLogger("controller")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


def bernstein_poly(i: int, n: int, t: np.ndarray) -> np.ndarray:
    return comb(n, i) * (t**i) * ((1.0 - t) ** (n - i))


def bezier_curve(points: np.ndarray, num_samples: int = 50) -> np.ndarray:
    n = len(points) - 1
    t = np.linspace(0.0, 1.0, num_samples)
    poly = np.array([bernstein_poly(i, n, t) for i in range(n + 1)])
    x_vals = np.dot(poly.T, points[:, 0])
    y_vals = np.dot(poly.T, points[:, 1])
    return np.column_stack([x_vals, y_vals])


def human_move_to(x: int, y: int, duration_sec: float = 0.35, jitter_px: int = 2) -> None:
    """Move mouse along a quadratic Bézier with slight jitter."""
    if pyautogui is None:
        raise RuntimeError("pyautogui not installed")
    start = np.array(pyautogui.position(), dtype=float)
    end = np.array([float(x), float(y)], dtype=float)
    mid = (start + end) / 2.0 + np.array([np.random.randint(-40, 40), np.random.randint(-40, 40)])
    pts = np.array([start, mid, end])
    path = bezier_curve(pts, num_samples=max(20, int(duration_sec * 60)))
    step_pause = duration_sec / max(len(path), 1)
    for px, py in path:
        jx = int(px + np.random.randint(-jitter_px, jitter_px + 1))
        jy = int(py + np.random.randint(-jitter_px, jitter_px + 1))
        pyautogui.moveTo(jx, jy, _pause=False)
        time.sleep(step_pause)


def grab_monitor(index: int = 1) -> np.ndarray:
    if mss is None:
        raise RuntimeError("mss not installed")
    with mss.mss() as sct:
        mon = sct.monitors[index]
        raw = sct.grab(mon)
        img = np.array(raw)[:, :, :3]
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


@dataclass
class MatchResult:
    found: bool
    confidence: float
    top_left: tuple[int, int] | None


def template_match_screen(template_path: Path, monitor_index: int = 1, threshold: float = 0.72) -> MatchResult:
    """
    Generic template match — useful for chart UI elements you supply as PNG under data/templates/.
    """
    if not template_path.is_file():
        return MatchResult(False, 0.0, None)
    screen = grab_monitor(monitor_index)
    tpl = cv2.imread(str(template_path))
    if tpl is None:
        return MatchResult(False, 0.0, None)
    res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        return MatchResult(True, float(max_val), (int(max_loc[0]), int(max_loc[1])))
    return MatchResult(False, float(max_val), None)


def motion_mask_diff(prev: np.ndarray, cur: np.ndarray, thresh: int = 25) -> np.ndarray:
    """Highlight regions with motion (generic; not game-specific)."""
    g1 = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(g1, g2)
    _, mask = cv2.threshold(diff, thresh, 255, cv2.THRESH_BINARY)
    return mask


def run_vision_demo(seconds: float = 5.0, on_frame: Callable[[np.ndarray], None] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    t0 = time.time()
    prev = None
    while time.time() - t0 < seconds:
        frame = grab_monitor(1)
        if prev is not None:
            mask = motion_mask_diff(prev, frame)
            if on_frame:
                on_frame(mask)
        prev = frame
        time.sleep(0.05)


if __name__ == "__main__":
    run_vision_demo(2.0)
