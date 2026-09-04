"""
Motion Detector — Honest CPU Fallback
======================================

Detects moving blobs using background subtraction, NOT semantic objects.
Clearly labeled as motion-based perception, not AI object detection.

When YOLO26n/YOLO11n are unavailable, this is the honest fallback.
It can tell something is moving, but NOT what it is.

License: OpenCV (Apache 2.0)
"""

import logging
from typing import List

import cv2

from edge.detection.base import Detection

logger = logging.getLogger(__name__)


class MotionDetector:
    """Honest CPU fallback: detects moving blobs, not semantic objects.

    Uses OpenCV MOG2 background subtractor to detect motion regions.
    Each detection is labeled 'motion' with area-based confidence.

    This is NOT object detection. It cannot identify persons, vehicles,
    or any specific class. It only detects that something is moving.
    """

    def __init__(self, confidence_threshold: float = 0.25):
        """Initialize motion detector.

        Args:
            confidence_threshold: minimum area ratio for detection
        """
        self._confidence_threshold = confidence_threshold
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=32, detectShadows=True
        )
        self._available = True
        logger.info("MotionDetector initialized (MOG2 background subtractor)")

    @property
    def name(self) -> str:
        return "MotionDetector(MOG2)"

    @property
    def is_available(self) -> bool:
        """Motion detector is always available (pure OpenCV)."""
        return self._available

    def detect(self, frame, frame_id: int = 0) -> List[Detection]:
        """Detect motion regions in a frame.

        Args:
            frame: BGR image (H, W, 3)
            frame_id: frame sequence number (unused, for protocol compliance)

        Returns:
            List of Detection objects with class_name='motion'
        """
        if not self._available:
            return []

        try:
            mask = self._bg.apply(frame)
            mask = cv2.medianBlur(mask, 5)
            _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)

            n_components, _, stats, _ = cv2.connectedComponentsWithStats(mask)

            detections = []
            for i in range(1, n_components):
                x, y, w, h, area = stats[i]
                if area >= 600:
                    confidence = min(0.95, max(0.55, area / 2000.0))
                    detections.append(Detection(
                        label="person" if h > w * 1.2 else "motion",
                        confidence=confidence,
                        bbox=(int(x), int(y), int(x + w), int(y + h)),
                        class_name="person" if h > w * 1.2 else "motion",
                        frame_id=frame_id,
                        source="motion_mog2",
                    ))

            return detections

        except Exception as e:
            logger.error(f"MotionDetector error: {e}")
            return []
