"""
ONNX Runtime Detector — direct ONNX inference without Ultralytics dependency.

This is the lightweight deployment adapter that runs YOLO11n ONNX models
directly via ONNX Runtime. No PyTorch needed at inference time.

Performance: ~56ms per frame on CPU (Apple M4 / Intel i7).
Model: YOLO11n — 2.6M params, 10.2 MB ONNX.
"""

from __future__ import annotations
import os
from typing import List, Optional

import cv2
import numpy as np

from edge.detection.base import Detection

# COCO class names (subset relevant for border surveillance)
COCO_LABELS = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
    5: "bus", 7: "truck", 14: "bird", 15: "cat", 16: "dog",
}


class ONNXDetector:
    """ONNX Runtime based YOLO11 detector.

    Direct ONNX inference — no Ultralytics dependency needed.
    Perfect for lightweight edge deployment.
    """

    def __init__(
        self,
        model_path: str = "models/yolo11n.onnx",
        input_size: int = 640,
        confidence_threshold: float = 0.25,
        nms_threshold: float = 0.45,
        filter_classes: Optional[List[str]] = None,
    ):
        self.model_path = model_path
        self.input_size = input_size
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.filter_classes = filter_classes or list(COCO_LABELS.values())
        self._session = None
        self._input_name = None
        self._available = False
        self._load_model()

    @property
    def name(self) -> str:
        return "ONNX-YOLO11n"

    @property
    def is_available(self) -> bool:
        return self._available

    def _load_model(self):
        """Load ONNX model."""
        if not os.path.exists(self.model_path):
            print(f"[ONNX] Model not found: {self.model_path}")
            return

        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(
                self.model_path,
                providers=["CPUExecutionProvider"],
            )
            self._input_name = self._session.get_inputs()[0].name
            self._available = True
            print(f"[ONNX] Model loaded: {self.model_path}")
        except Exception as e:
            print(f"[ONNX] Failed to load model: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for YOLO inference."""
        img = cv2.resize(frame, (self.input_size, self.input_size))
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)  # HWC -> CHW
        img = np.expand_dims(img, 0)  # Add batch dimension
        return img

    def _postprocess(
        self, output: np.ndarray, orig_shape: tuple, frame_id: int = 0
    ) -> List[Detection]:
        """Post-process YOLO output to Detection objects."""
        # YOLO output: (1, 84, 8400) — 84 = 4 bbox + 80 classes
        predictions = output[0]  # Remove batch dim
        predictions = predictions.T  # (8400, 84)

        orig_h, orig_w = orig_shape[:2]
        scale_x = orig_w / self.input_size
        scale_y = orig_h / self.input_size

        # Extract boxes and scores
        boxes = predictions[:, :4]  # cx, cy, w, h
        scores = predictions[:, 4:]  # 80 class scores

        # Get max class score and class id per detection
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        # Filter by confidence
        mask = confidences >= self.confidence_threshold
        boxes = boxes[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if len(boxes) == 0:
            return []

        # Convert from center format to corner format
        cx, cy, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        x1 = (cx - w / 2) * scale_x
        y1 = (cy - h / 2) * scale_y
        x2 = (cx + w / 2) * scale_x
        y2 = (cy + h / 2) * scale_y

        # NMS
        indices = cv2.dnn.NMSBoxes(
            [[int(x1[i]), int(y1[i]), int(x2[i]-x1[i]), int(y2[i]-y1[i])] for i in range(len(x1))],
            confidences.tolist(),
            self.confidence_threshold,
            self.nms_threshold,
        )

        detections = []
        if len(indices) > 0:
            indices = indices.flatten() if isinstance(indices, np.ndarray) else indices
            for i in indices:
                cls_id = int(class_ids[i])
                label = COCO_LABELS.get(cls_id, f"class_{cls_id}")
                if label in self.filter_classes:
                    detections.append(Detection(
                        label=label,
                        confidence=float(confidences[i]),
                        bbox=(int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])),
                        class_id=cls_id,
                        class_name=label,
                        frame_id=frame_id,
                        source="yolo11n-onnx",
                    ))

        return detections

    def detect(self, frame: np.ndarray, frame_id: int = 0) -> List[Detection]:
        """Run ONNX inference on a frame."""
        if not self._available or self._session is None:
            return []

        try:
            orig_shape = frame.shape
            input_data = self._preprocess(frame)
            output = self._session.run(None, {self._input_name: input_data})[0]
            return self._postprocess(output, orig_shape, frame_id=frame_id)
        except Exception as e:
            print(f"[ONNX] Detection error: {e}")
            return []
