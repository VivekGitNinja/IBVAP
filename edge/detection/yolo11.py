"""
YOLO11 Detector Adapter — uses Ultralytics for inference.

Detects: persons, vehicles, and 80 COCO classes.
CPU-friendly with ONNX Runtime backend.
Honest labeling: "YOLO11n AI detection" not "person detection".
"""

from __future__ import annotations
import os
from typing import List, Optional

import numpy as np

from edge.detection.base import Detection

# COCO class names relevant to border surveillance
RELEVANT_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    14: "bird",
    15: "cat",
    16: "dog",
}

# All 80 COCO class names
COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


class YOLO11Detector:
    """YOLO11 object detector using Ultralytics.

    Falls back gracefully if model is unavailable.
    Uses ONNX Runtime for CPU inference.
    """

    def __init__(
        self,
        model_path: str = "models/yolo11n.onnx",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        filter_classes: Optional[List[str]] = None,
        border_only: bool = False,
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.border_only = border_only
        self.filter_classes = filter_classes or ["person", "car", "truck", "bus", "motorcycle", "bicycle"]
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self):
        """Try to load the YOLO11 model."""
        try:
            from ultralytics import YOLO
            candidate_paths = [
                self.model_path,
                "models/yolo11n.pt",
                "yolo11n.pt",
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    self._model = YOLO(p)
                    self._available = True
                    print(f"[YOLO11] Model loaded: {p}")
                    return
            # Fallback attempt by name
            self._model = YOLO("yolo11n.pt")
            self._available = True
            print(f"[YOLO11] Model loaded from ultralytics cache")
        except Exception as e:
            print(f"[YOLO11] Model not available: {e}")
            self._available = False

    @property
    def name(self) -> str:
        return "YOLO11n"

    @property
    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray, frame_id: int = 0) -> List[Detection]:
        """Run YOLO11 detection on a frame.

        Returns Detection objects with real AI inference results.
        Falls back to empty list if model unavailable.
        """
        if not self._available or self._model is None:
            return []

        try:
            results = self._model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                verbose=False,
            )

            detections = []
            for result in results:
                if result.boxes is None:
                    continue
                boxes = result.boxes
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    conf = float(boxes.conf[i].item())
                    x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().astype(int)

                    class_name = COCO_NAMES[cls_id] if cls_id < len(COCO_NAMES) else f"class_{cls_id}"

                    # Filter to relevant classes for border surveillance
                    if class_name in self.filter_classes:
                        detections.append(Detection(
                            label=class_name,
                            confidence=conf,
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            class_id=cls_id,
                            class_name=class_name,
                            frame_id=frame_id,
                            source="yolo11n",
                        ))

            return detections

        except Exception as e:
            print(f"[YOLO11] Detection error: {e}")
            return []
