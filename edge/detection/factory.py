"""
Detector Factory — Auto-select the best available detector
==========================================================

Priority order:
1. YOLO26n (Ultralytics) — World's fastest edge detector, 40.9 mAP, 38.9ms CPU
2. YOLO11n (Ultralytics) — Stable fallback, 39.5 mAP, 56ms CPU
3. ONNX Runtime — Direct ONNX inference
4. Motion (OpenCV MOG2) — Honest fallback, motion-only

Each detector implements the Detector protocol from base.py.
The factory automatically selects the best available option.
"""

import logging
from typing import Optional

from edge.detection.base import Detector

logger = logging.getLogger(__name__)


def create_detector(
    preferred: Optional[str] = None,
    confidence_threshold: float = 0.25,
    border_only: bool = False,
    **kwargs,
) -> Detector:
    """Create the best available detector.
    
    Args:
        preferred: preferred detector name ('yolo26', 'yolo11', 'onnx', 'motion')
        confidence_threshold: minimum detection confidence
        border_only: if True, only detect border-relevant classes
        **kwargs: additional detector configurations (e.g. min_area, persistence_frames, conf_floor)
    
    Returns:
        Best available Detector instance
    """
    if preferred:
        detector = _try_create(preferred, confidence_threshold, border_only, **kwargs)
        if detector and detector.is_available:
            logger.info(f"Using preferred detector: {detector.name}")
            return detector
        logger.warning(f"Preferred detector '{preferred}' not available, auto-selecting")

    # Auto-select: try in order of capability
    for name in ["yolo26", "yolo11", "onnx", "motion"]:
        detector = _try_create(name, confidence_threshold, border_only, **kwargs)
        if detector and detector.is_available:
            logger.info(f"Auto-selected detector: {detector.name}")
            return detector

    # Should never reach here (motion always available)
    from edge.detection.motion import MotionDetector
    return MotionDetector(
        confidence_threshold=confidence_threshold,
        min_area=kwargs.get("min_area", 600),
        persistence_frames=kwargs.get("persistence_frames", 3),
        conf_floor=kwargs.get("conf_floor", 0.55),
    )


def _try_create(
    name: str,
    confidence_threshold: float,
    border_only: bool,
    **kwargs,
) -> Optional[Detector]:
    """Try to create a specific detector supporting various aliases."""
    if not name:
        return None

    norm = name.lower().strip().replace("-", "").replace("_", "")

    try:
        if norm.startswith("yolo26"):
            from edge.detection.yolo26 import YOLO26Detector
            model_size = "s" if norm.endswith("s") else "n"
            return YOLO26Detector(
                model_size=model_size,
                confidence_threshold=confidence_threshold,
                border_only=border_only,
            )
        elif norm.startswith("yolo11"):
            from edge.detection.yolo11 import YOLO11Detector
            return YOLO11Detector(
                confidence_threshold=confidence_threshold,
                border_only=border_only,
            )
        elif norm.startswith("onnx"):
            from edge.detection.onnx_detector import ONNXDetector
            return ONNXDetector(confidence_threshold=confidence_threshold)
        elif norm.startswith("motion") or "mog" in norm:
            from edge.detection.motion import MotionDetector
            return MotionDetector(
                confidence_threshold=confidence_threshold,
                min_area=kwargs.get("min_area", 600),
                persistence_frames=kwargs.get("persistence_frames", 3),
                conf_floor=kwargs.get("conf_floor", 0.55),
            )
    except Exception as e:
        logger.debug(f"Failed to create {name} detector: {e}")
    return None


def list_available_detectors():
    """List all available detectors with status."""
    detectors = {}
    for name in ["yolo26", "yolo11", "onnx", "motion"]:
        d = _try_create(name, 0.25, False)
        detectors[name] = {
            "available": d.is_available if d else False,
            "name": d.name if d else name,
        }
    return detectors
