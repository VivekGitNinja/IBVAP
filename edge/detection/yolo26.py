"""
YOLO26 Detector Adapter — World's Best Edge Object Detector
==========================================================

YOLO26 is the latest (Sept 2025) edge-first object detector from Ultralytics:
- 40.9 mAP on COCO (nano)
- 38.9ms CPU inference (45% faster than YOLO11)
- 2.4M parameters (nano), 9.5M (small)
- NMS-free inference
- 80 COCO classes including person, car, truck, motorcycle, bus
- ONNX export ready

License: AGPL-3.0 (Ultralytics)
Source: https://github.com/ultralytics/ultralytics
"""

import os
import time
import logging
from typing import List, Optional

from edge.detection.base import Detector, Detection

logger = logging.getLogger(__name__)

# COCO classes relevant for border surveillance
BORDER_RELEVANT_CLASSES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
    5: "bus", 7: "truck", 14: "bird", 15: "cat",
    16: "dog", 19: "backpack", 24: "handbag", 25: "suitcase",
}

# Classes that are always detected (all 80 COCO)
ALL_COCO_CLASSES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep",
    19: "cow", 20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe",
    24: "backpack", 25: "umbrella", 26: "handbag", 27: "tie",
    28: "suitcase", 29: "frisbee", 30: "skis", 31: "snowboard",
    32: "sports ball", 33: "kite", 34: "baseball bat", 35: "baseball glove",
    36: "skateboard", 37: "surfboard", 38: "tennis racket", 39: "bottle",
    40: "wine glass", 41: "cup", 42: "fork", 43: "knife", 44: "spoon",
    45: "bowl", 46: "banana", 47: "apple", 48: "sandwich", 49: "orange",
    50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza", 54: "donut",
    55: "cake", 56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
    60: "dining table", 61: "toilet", 62: "tv", 63: "laptop",
    64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone",
    68: "microwave", 69: "oven", 70: "toaster", 71: "sink",
    72: "refrigerator", 73: "book", 74: "clock", 75: "vase",
    76: "scissors", 77: "teddy bear", 78: "hair drier", 79: "toothbrush",
}


class YOLO26Detector(Detector):
    """YOLO26 detector — world's fastest edge object detector.
    
    Uses Ultralytics YOLO26n (nano) as default for maximum speed on CPU.
    Falls back to YOLO26s (small) if configured for higher accuracy.
    """

    def __init__(
        self,
        model_size: str = "n",
        confidence_threshold: float = 0.25,
        border_only: bool = False,
        device: str = "cpu",
    ):
        """
        Args:
            model_size: 'n' for nano (fastest), 's' for small (better accuracy)
            confidence_threshold: minimum confidence for detections
            border_only: if True, only return border-relevant classes
            device: 'cpu' or 'cuda'
        """
        self.confidence_threshold = confidence_threshold
        self.border_only = border_only
        self.device = device
        self.model = None
        self.model_name = f"yolo26{model_size}"
        self._available = False
        self._class_names = ALL_COCO_CLASSES

        # Try to load the model
        self._load_model(model_size)

    def _load_model(self, model_size: str) -> None:
        """Load YOLO26 model."""
        try:
            from ultralytics import YOLO

            model_path = f"models/yolo26{model_size}.pt"
            if not os.path.exists(model_path):
                model_path = f"yolo26{model_size}.pt"

            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                self._available = True
                logger.info(f"Loaded YOLO26{model_size} from {model_path}")
            else:
                # Auto-download
                self.model = YOLO(f"yolo26{model_size}.pt")
                self._available = True
                logger.info(f"Downloaded and loaded YOLO26{model_size}")
        except Exception as e:
            logger.warning(f"Failed to load YOLO26{model_size}: {e}")
            self._available = False

    @property
    def name(self) -> str:
        return f"YOLO26{self.model_size}{'(border)' if self.border_only else ''}"

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def model_size(self) -> str:
        return "n" if "n" in self.model_name else "s"

    def detect(self, frame, frame_id: int = 0) -> List[Detection]:
        """Run YOLO26 detection on a frame.
        
        Args:
            frame: numpy array (H, W, 3) BGR or RGB
            frame_id: frame sequence number
            
        Returns:
            List of Detection objects
        """
        if not self._available or self.model is None:
            return []

        try:
            import cv2
            import numpy as np

            start_time = time.time()

            # Run inference
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False,
            )

            detections = []
            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        class_name = self._class_names.get(cls_id, f"class_{cls_id}")

                        # Filter for border-relevant classes if configured
                        if self.border_only and cls_id not in BORDER_RELEVANT_CLASSES:
                            continue

                        detections.append(Detection(
                            bbox=[float(x1), float(y1), float(x2), float(y2)],
                            class_id=cls_id,
                            class_name=class_name,
                            confidence=conf,
                            frame_id=frame_id,
                            center=[
                                (float(x1) + float(x2)) / 2,
                                (float(y1) + float(y2)) / 2,
                            ],
                        ))

            inference_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"YOLO26: {len(detections)} detections in {inference_ms:.1f}ms"
            )

            return detections

        except Exception as e:
            logger.error(f"YOLO26 detection error: {e}")
            return []
