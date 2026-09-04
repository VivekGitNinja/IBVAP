from __future__ import annotations
"""
Camera Health Intelligence.

Detects:
- Online/offline
- Frame freeze
- Low FPS
- Black screen
- Excessive brightness
- Excessive darkness
- Stream interruption

Returns a health score (0-100) and detailed metrics.
"""

import time
import cv2
import numpy as np
from datetime import datetime


def blur_score(frame: np.ndarray) -> float:
    """Compute image blur score via Laplacian variance."""
    return float(cv2.Laplacian(frame, cv2.CV_64F).var())


def brightness(frame: np.ndarray) -> float:
    """Compute mean brightness (0-255)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def frozen_score(previous: np.ndarray | None, current: np.ndarray) -> float:
    """Compute frame-to-frame difference. Low values = frozen frame."""
    if previous is None:
        return 0.0
    diff = cv2.absdiff(previous, current)
    return float(np.mean(diff))


def black_screen_score(frame: np.ndarray) -> float:
    """Check if frame is predominantly black."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def frame_fps_estimate(frame_times: list[float], window: int = 30) -> float:
    """Estimate FPS from recent frame timestamps."""
    if len(frame_times) < 2:
        return 0.0
    recent = frame_times[-window:]
    if len(recent) < 2:
        return 0.0
    duration = recent[-1] - recent[0]
    if duration <= 0:
        return 0.0
    return (len(recent) - 1) / duration


def health_score(
    frame: np.ndarray,
    previous: np.ndarray | None = None,
    expected_fps: float = 10.0,
    frame_times: list[float] | None = None,
) -> tuple[float, dict]:
    """Compute comprehensive camera health score.

    Returns:
        (score, metadata) where score is 0-100
    """
    meta = {}
    score = 100.0

    # Blur detection
    b = blur_score(frame)
    meta["blur"] = round(b, 2)
    if b < 20:
        score -= 30
        meta["blur_warning"] = "Very blurry"
    elif b < 50:
        score -= 15
        meta["blur_warning"] = "Slightly blurry"

    # Brightness
    br = brightness(frame)
    meta["brightness"] = round(br, 2)
    if br < 5:
        score -= 35
        meta["brightness_warning"] = "Black screen"
    elif br < 15:
        score -= 25
        meta["brightness_warning"] = "Very dark"
    elif br > 250:
        score -= 25
        meta["brightness_warning"] = "Overexposed"
    elif br > 240:
        score -= 10
        meta["brightness_warning"] = "Bright"

    # Frame freeze
    fr = frozen_score(previous, frame)
    meta["frame_delta"] = round(fr, 2)
    if previous is not None and fr < 0.3:
        score -= 30
        meta["freeze_warning"] = "Frame appears frozen"
    elif previous is not None and fr < 1.0:
        score -= 10
        meta["freeze_warning"] = "Minimal frame change"

    # FPS estimation
    if frame_times:
        fps = frame_fps_estimate(frame_times)
        meta["fps_estimated"] = round(fps, 1)
        if expected_fps > 0 and fps < expected_fps * 0.5:
            score -= 15
            meta["fps_warning"] = f"Low FPS: {fps:.1f}"

    # Resolution
    h, w = frame.shape[:2]
    meta["resolution"] = f"{w}x{h}"
    meta["width"] = w
    meta["height"] = h

    score = max(0.0, min(100.0, score))

    # Determine status
    if score >= 80:
        status = "HEALTHY"
    elif score >= 50:
        status = "DEGRADED"
    else:
        status = "OFFLINE"
    meta["status"] = status

    return score, meta


class CameraHealthChecker:
    """Camera health monitoring using frame analysis."""

    def __init__(self, expected_fps: float = 10.0):
        self.expected_fps = expected_fps
        self._prev_frame = None
        self._frame_times = []

    def check_frame(self, frame: np.ndarray, inference_ms: float = 0) -> dict:
        """Analyze frame and return health metrics."""
        now = time.time()
        self._frame_times.append(now)
        if len(self._frame_times) > 60:
            self._frame_times = self._frame_times[-60:]

        score, meta = health_score(
            frame, self._prev_frame, self.expected_fps, self._frame_times
        )
        self._prev_frame = frame.copy()
        meta["inference_ms"] = round(inference_ms, 1)
        meta["health_score"] = round(score, 1)
        return meta
