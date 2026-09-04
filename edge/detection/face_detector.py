"""
Face Detection Adapter — Privacy-Preserving Face Analytics
==========================================================

Lightweight face detection for:
- Face count and location tracking
- Privacy mode (blur/redaction)
- Optional candidate matching (NOT autonomous identification)
- All results require human verification

Uses OpenCV DNN with a lightweight face detection model.
Falls back to Haar cascade if DNN model unavailable.

IMPORTANT: This module detects faces only.
It does NOT perform facial recognition or identification.
Any matching functionality is candidate-only with human verification.

License: Apache 2.0 (OpenCV models)
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Single face detection result."""
    bbox: List[float] = field(default_factory=lambda: [0, 0, 0, 0])
    confidence: float = 0.0
    landmarks: Optional[List[List[float]]] = None
    frame_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "confidence": round(self.confidence, 3),
            "has_landmarks": self.landmarks is not None,
        }


class FaceDetector:
    """Lightweight face detector with multiple backend support.
    
    Detection only — no recognition or identification.
    Used for:
    - Counting faces in frame
    - Privacy blur/redaction zones
    - Behavior analysis (facing direction, group detection)
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Args:
            confidence_threshold: minimum confidence for face detections
        """
        self.confidence_threshold = confidence_threshold
        self._net = None
        self._cascade = None
        self._available = False
        self._method = "none"

        self._init_detector()

    def _init_detector(self):
        """Try to initialize the best available face detector."""
        # Method 1: OpenCV DNN (Caffe model)
        caffemodel = cv2.data.haarcascades.replace(
            "haarcascades/", ""
        ) + "opencv_face_detector_uint8.pb"
        prototxt = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "models", "opencv_face_detector.pbtxt"
        )

        # Try standard OpenCV DNN face model paths
        dnn_paths = [
            ("models/opencv_face_detector_uint8.pb",
             "models/opencv_face_detector.pbtxt"),
            ("models/face_detector_uint8.pb",
             "models/face_detector.pbtxt"),
        ]

        for pb_path, pbtxt_path in dnn_paths:
            if os.path.exists(pb_path) and os.path.exists(pbtxt_path):
                try:
                    self._net = cv2.dnn.readNetFromTensorflow(pb_path, pbtxt_path)
                    self._available = True
                    self._method = "dnn"
                    logger.info(f"Loaded DNN face detector from {pb_path}")
                    return
                except Exception as e:
                    logger.warning(f"DNN load failed: {e}")

        # Method 2: Haar cascade (always available)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(cascade_path):
            self._cascade = cv2.CascadeClassifier(cascade_path)
            self._available = True
            self._method = "haar_cascade"
            logger.info("Using Haar cascade face detector")

    @property
    def name(self) -> str:
        return f"FaceDetector({self._method})"

    @property
    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray, frame_id: int = 0) -> List[FaceDetection]:
        """Detect faces in frame.
        
        Args:
            frame: BGR image (H, W, 3)
            frame_id: frame sequence number
            
        Returns:
            List of FaceDetection objects
        """
        if not self._available:
            return []

        try:
            if self._method == "dnn":
                return self._detect_dnn(frame, frame_id)
            elif self._method == "haar_cascade":
                return self._detect_haar(frame, frame_id)
        except Exception as e:
            logger.error(f"Face detection error: {e}")

        return []

    def _detect_dnn(self, frame: np.ndarray, frame_id: int) -> List[FaceDetection]:
        """DNN-based face detection."""
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300),
            (104.0, 177.0, 123.0)
        )
        self._net.setInput(blob)
        detections = self._net.forward()

        faces = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < self.confidence_threshold:
                continue

            x1 = int(detections[0, 0, i, 3] * w)
            y1 = int(detections[0, 0, i, 4] * h)
            x2 = int(detections[0, 0, i, 5] * w)
            y2 = int(detections[0, 0, i, 6] * h)

            faces.append(FaceDetection(
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                confidence=confidence,
                frame_id=frame_id,
            ))

        return faces

    def _detect_haar(self, frame: np.ndarray, frame_id: int) -> List[FaceDetection]:
        """Haar cascade face detection."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_rect = self._cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        results = []
        for (x, y, w, h) in faces_rect:
            # Haar cascade doesn't provide confidence, estimate from neighbors
            confidence = 0.7  # Moderate confidence for haar
            results.append(FaceDetection(
                bbox=[float(x), float(y), float(x + w), float(y + h)],
                confidence=confidence,
                frame_id=frame_id,
            ))

        return results

    def blur_faces(
        self, frame: np.ndarray, faces: List[FaceDetection],
        blur_strength: int = 99
    ) -> np.ndarray:
        """Apply Gaussian blur to detected face regions.
        
        Privacy mode: blur all faces in frame.
        """
        result = frame.copy()
        for face in faces:
            x1, y1, x2, y2 = [int(b) for b in face.bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 > x1 and y2 > y1:
                roi = result[y1:y2, x1:x2]
                blurred = cv2.GaussianBlur(roi, (blur_strength, blur_strength), 30)
                result[y1:y2, x1:x2] = blurred

        return result

    def draw_detections(
        self, frame: np.ndarray, faces: List[FaceDetection]
    ) -> np.ndarray:
        """Draw face detection boxes on frame."""
        result = frame.copy()
        for face in faces:
            x1, y1, x2, y2 = [int(b) for b in face.bbox]
            cv2.rectangle(result, (x1, y1), (x2, y2), (0, 255, 255), 2)
            label = f"Face {face.confidence:.2f}"
            cv2.putText(result, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        return result
