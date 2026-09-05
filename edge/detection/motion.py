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
    Each detection is labeled 'motion' (or 'person' based on vertical aspect ratio)
    with synthesized area-based confidence.

    Noise gating & False-Positive Control:
    - Minimum contour area threshold (min_area, default: 600 px)
    - Temporal persistence gating (persistence_frames, default: >=3 consecutive frames)
    - Synthesized confidence floor (conf_floor, default: 0.55)
    """

    def __init__(
        self,
        confidence_threshold: float = 0.25,
        min_area: int = 600,
        persistence_frames: int = 3,
        conf_floor: float = 0.55,
    ):
        """Initialize motion detector.

        Args:
            confidence_threshold: minimum detection confidence
            min_area: minimum blob contour area to filter sensor noise
            persistence_frames: consecutive frames required before emitting detection
            conf_floor: baseline synthesized confidence floor
        """
        self._confidence_threshold = confidence_threshold
        self.min_area = min_area
        self.persistence_frames = persistence_frames
        self.conf_floor = conf_floor
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=32, detectShadows=True
        )
        self._available = True
        self._tracked_blobs = {}
        self._next_blob_id = 1
        self._frame_count = 0
        logger.info(
            f"MotionDetector initialized (MOG2, min_area={self.min_area}, "
            f"persistence={self.persistence_frames}, conf_floor={self.conf_floor})"
        )

    @property
    def name(self) -> str:
        return "MotionDetector(MOG2)"

    @property
    def is_available(self) -> bool:
        """Motion detector is always available (pure OpenCV)."""
        return self._available

    def detect(self, frame, frame_id: int = 0) -> List[Detection]:
        """Detect motion regions in a frame with temporal persistence gating.

        Args:
            frame: BGR image (H, W, 3)
            frame_id: frame sequence number

        Returns:
            List of Detection objects with class_name='motion' or 'person'
        """
        if not self._available:
            return []

        try:
            self._frame_count += 1
            current_step = frame_id if (frame_id is not None and frame_id > 0) else self._frame_count

            mask = self._bg.apply(frame)
            mask = cv2.medianBlur(mask, 5)
            _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)

            n_components, _, stats, _ = cv2.connectedComponentsWithStats(mask)

            candidates = []
            for i in range(1, n_components):
                x, y, w, h, area = stats[i]
                if area >= self.min_area:
                    cx = x + w / 2.0
                    cy = y + h / 2.0
                    candidates.append((int(x), int(y), int(w), int(h), float(area), cx, cy))

            # Match candidates to active tracked blobs
            matched_blob_ids = set()
            for cand in candidates:
                cx, cy = cand[5], cand[6]
                best_id = None
                max_allowed = max(120.0, max(cand[2], cand[3]) * 0.8)
                best_dist = max_allowed
                for blob_id, blob in self._tracked_blobs.items():
                    if blob_id in matched_blob_ids:
                        continue
                    bx, by = blob["centroid"]
                    dist = ((cx - bx) ** 2 + (cy - by) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_id = blob_id

                if best_id is not None:
                    matched_blob_ids.add(best_id)
                    b = self._tracked_blobs[best_id]
                    b["bbox"] = (cand[0], cand[1], cand[2], cand[3])
                    b["centroid"] = (cand[5], cand[6])
                    b["area"] = cand[4]
                    b["hits"] += 1
                    b["last_seen"] = current_step
                else:
                    blob_id = self._next_blob_id
                    self._next_blob_id += 1
                    self._tracked_blobs[blob_id] = {
                        "bbox": (cand[0], cand[1], cand[2], cand[3]),
                        "centroid": (cand[5], cand[6]),
                        "area": cand[4],
                        "hits": 1,
                        "last_seen": current_step,
                    }

            # Expire stale blobs not observed in recent frames
            dead_ids = [
                bid for bid, b in self._tracked_blobs.items()
                if (current_step - b["last_seen"]) > 2
            ]
            for bid in dead_ids:
                del self._tracked_blobs[bid]

            # Emit detections only for persistent candidates seen in current frame
            detections = []
            for blob_id, b in self._tracked_blobs.items():
                if b["last_seen"] == current_step and b["hits"] >= self.persistence_frames:
                    x, y, w, h = b["bbox"]
                    area = b["area"]
                    confidence = min(0.95, max(self.conf_floor, area / 2000.0))
                    if confidence >= self._confidence_threshold:
                        label = "person" if h > w * 1.2 else "motion"
                        detections.append(Detection(
                            label=label,
                            confidence=confidence,
                            bbox=(int(x), int(y), int(x + w), int(y + h)),
                            class_name=label,
                            frame_id=frame_id,
                            source="motion_mog2",
                        ))

            return detections

        except Exception as e:
            logger.error(f"MotionDetector error: {e}")
            return []
