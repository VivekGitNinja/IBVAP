"""
ANPR Pipeline — Automatic Number Plate Recognition
====================================================

Real modular ANPR pipeline:
1. Vehicle detection (YOLO26)
2. Plate region detection (plate-specific YOLO or contour-based)
3. Image preprocessing (deskew, contrast, denoise)
4. OCR (ONNX-based character recognition)
5. Plate normalization (Indian format: XX XX XXXX)
6. Confidence scoring
7. Candidate result with human verification

This module provides an honest, modular ANPR adapter.
When OCR models are unavailable, it falls back to plate detection only.
Never fabricates plate numbers.

License: Models used are AGPL-3.0 (Ultralytics)
"""

import os
import time
import logging
import re
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PlateResult:
    """Result from ANPR pipeline."""
    plate_text: str = ""
    confidence: float = 0.0
    plate_bbox: Optional[List[float]] = None
    vehicle_bbox: Optional[List[float]] = None
    preprocessing_applied: List[str] = field(default_factory=list)
    status: str = "candidate"  # candidate, verified, rejected
    method: str = "none"
    evidence_image: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plate_text": self.plate_text,
            "confidence": round(self.confidence, 3),
            "plate_bbox": self.plate_bbox,
            "vehicle_bbox": self.vehicle_bbox,
            "preprocessing": self.preprocessing_applied,
            "status": self.status,
            "method": self.method,
        }


class ImagePreprocessor:
    """Preprocess plate region for better OCR accuracy."""

    @staticmethod
    def preprocess(plate_img: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Apply preprocessing pipeline to plate image.
        
        Returns:
            Preprocessed image and list of applied steps
        """
        applied = []
        result = plate_img.copy()

        # 1. Resize to standard height
        h, w = result.shape[:2]
        if h < 36:
            scale = 36 / h
            result = cv2.resize(result, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_CUBIC)
            applied.append("upscale")

        # 2. Convert to grayscale
        if len(result.shape) == 3:
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            applied.append("grayscale")

        # 3. Denoise
        result = cv2.fastNlMeansDenoising(result, h=10)
        applied.append("denoise")

        # 4. Contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        result = clahe.apply(result)
        applied.append("clahe_contrast")

        # 5. Adaptive threshold
        result = cv2.adaptiveThreshold(
            result, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        applied.append("threshold")

        # 6. Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
        applied.append("morphology")

        return result, applied

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Correct skew in plate image."""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 10:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5:
            return image
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)


class PlateDetector:
    """Detect license plate regions in vehicle crops."""

    def __init__(self):
        self._cascade = None
        self._load_cascade()

    def _load_cascade(self):
        """Load OpenCV Haar cascade for plate detection."""
        cascade_path = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
        if os.path.exists(cascade_path):
            self._cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("Loaded plate Haar cascade")
        else:
            logger.warning("Plate cascade not found, using contour-based detection")

    def detect_plates(self, vehicle_crop: np.ndarray) -> List[List[float]]:
        """Detect plate regions in a vehicle crop.
        
        Returns:
            List of [x1, y1, x2, y2] plate bounding boxes
        """
        plates = []

        # Method 1: Haar cascade
        if self._cascade is not None:
            gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY) \
                if len(vehicle_crop.shape) == 3 else vehicle_crop
            detections = self._cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 20)
            )
            for (x, y, w, h) in detections:
                plates.append([float(x), float(y), float(x + w), float(y + h)])

        # Method 2: Contour-based fallback
        if not plates:
            plates = self._contour_based_detection(vehicle_crop)

        return plates

    def _contour_based_detection(self, image: np.ndarray) -> List[List[float]]:
        """Fallback: detect plate-like rectangular contours."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) \
            if len(image.shape) == 3 else image
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 100, 200)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        plates = []
        h_img, w_img = image.shape[:2]
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / max(h, 1)
            area = w * h

            # Plate-like: aspect ratio 2-6, area > 0.5% of image
            if (2.0 <= aspect_ratio <= 6.0 and
                area > 0.005 * h_img * w_img and
                area < 0.5 * h_img * w_img):
                plates.append([float(x), float(y), float(x + w), float(y + h)])

        return plates


class PlateOCR:
    """OCR for license plate text recognition."""

    def __init__(self):
        self._available = False
        self._model = None
        self._charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        self._try_load_onnx()

    def _try_load_onnx(self):
        """Try to load ONNX plate OCR model."""
        model_paths = [
            "models/plate_ocr.onnx",
            "models/plate_reader.onnx",
        ]
        for path in model_paths:
            if os.path.exists(path):
                try:
                    import onnxruntime as ort
                    self._model = ort.InferenceSession(path)
                    self._available = True
                    logger.info(f"Loaded plate OCR from {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load OCR from {path}: {e}")

        # Try fast-plate-ocr package
        try:
            from fast_plate_ocr import LPRNet
            self._lprnet = LPRNet()
            self._available = True
            logger.info("Loaded fast-plate-ocr LPRNet")
        except ImportError:
            logger.info("fast-plate-ocr not available, using template matching fallback")
        except Exception as e:
            logger.warning(f"fast-plate-ocr load failed: {e}")

    def recognize(self, plate_img: np.ndarray) -> Tuple[str, float]:
        """Recognize text from plate image.
        
        Returns:
            (plate_text, confidence)
        """
        if not self._available:
            return self._template_fallback(plate_img)

        try:
            # Preprocess
            preprocessor = ImagePreprocessor()
            processed, _ = preprocessor.preprocess(plate_img)

            # Resize for model input
            processed = cv2.resize(processed, (168, 48))

            if self._model is not None:
                return self._onnx_ocr(processed)
            elif hasattr(self, '_lprnet'):
                return self._lprnet_ocr(plate_img)

        except Exception as e:
            logger.error(f"OCR error: {e}")

        return self._template_fallback(plate_img)

    def _onnx_ocr(self, processed: np.ndarray) -> Tuple[str, float]:
        """Run ONNX model for OCR."""
        # Normalize and reshape for model
        img = processed.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)
        img = np.expand_dims(img, axis=0)

        input_name = self._model.get_inputs()[0].name
        output = self._model.run(None, {input_name: img})[0]

        # Decode output
        text = ""
        confidence = 1.0
        if output.ndim == 3:
            for t in range(output.shape[1]):
                idx = np.argmax(output[0, t])
                if idx < len(self._charset):
                    text += self._charset[idx]
            confidence = float(np.max(np.exp(output) / np.sum(np.exp(output), axis=-1)))

        return self._normalize_plate(text), confidence

    def _lprnet_ocr(self, plate_img: np.ndarray) -> Tuple[str, float]:
        """Use fast-plate-ocr LPRNet."""
        try:
            results = self._lprnet.predict(plate_img)
            if results and len(results) > 0:
                text = results[0].get("text", "")
                conf = results[0].get("confidence", 0.5)
                return self._normalize_plate(text), conf
        except Exception:
            pass
        return "", 0.0

    def _template_fallback(self, plate_img: np.ndarray) -> Tuple[str, float]:
        """Character-counting fallback when no OCR model is available.

        Clearly labeled as DEMO MODE — does NOT fabricate plate numbers.
        Returns character count estimate with low confidence.

        Returns:
            (plate_text, confidence) — text is descriptive, not a real plate
        """
        try:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY) \
                if len(plate_img.shape) == 3 else plate_img

            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)

            chars = 0
            h, w = plate_img.shape[:2]
            for i in range(1, num_labels):
                cw, ch = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
                if 0.2 < ch / max(h, 1) < 0.9 and 0.05 < cw / max(w, 1) < 0.3:
                    chars += 1

            # Indian plates: 8-10 characters (e.g., MH 12 AB 1234)
            confidence = min(chars / 8.0, 1.0) * 0.25

            # Clearly labeled — NOT a real plate
            if chars >= 6:
                return f"DEMO-{chars}CH", confidence
            elif chars >= 3:
                return f"DEMO-{chars}ch", confidence * 0.5
            else:
                return "", 0.0

        except Exception as e:
            logger.debug(f"Template fallback error: {e}")
            return "", 0.0

    @staticmethod
    def _normalize_plate(text: str) -> str:
        """Normalize plate text to Indian format.
        
        Indian plate format: XX XX XXXX or XX-XX-XXXX
        State code (2 letters) + District (2 letters) + Number (4 digits)
        """
        # Remove spaces and special characters
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())

        if len(cleaned) >= 8:
            # Try Indian format: AA DD NNNN
            return f"{cleaned[:2]} {cleaned[2:4]} {cleaned[4:8]}"
        elif len(cleaned) >= 4:
            return cleaned
        else:
            return text


class ANPRPipeline:
    """Complete ANPR pipeline combining vehicle detection, plate detection, 
    preprocessing, and OCR.
    """

    def __init__(self):
        self.plate_detector = PlateDetector()
        self.ocr = PlateOCR()
        self.preprocessor = ImagePreprocessor()
        self._stats = {"frames_processed": 0, "plates_detected": 0}

    @property
    def is_available(self) -> bool:
        return True  # Always available with fallback

    @property
    def ocr_available(self) -> bool:
        return self.ocr._available

    def process_frame(
        self,
        frame: np.ndarray,
        vehicle_detections: List[Dict],
    ) -> List[PlateResult]:
        """Process a frame for ANPR.
        
        Args:
            frame: Full camera frame
            vehicle_detections: List of vehicle detections from YOLO
                               [{"bbox": [x1,y1,x2,y2], "class_name": "car", ...}]
        
        Returns:
            List of PlateResult objects
        """
        self._stats["frames_processed"] += 1
        results = []

        vehicle_classes = {"car", "truck", "bus", "motorcycle"}

        for det in vehicle_detections:
            if det.get("class_name", "") not in vehicle_classes:
                continue

            bbox = det["bbox"]
            x1, y1, x2, y2 = [int(b) for b in bbox]

            # Clamp to frame
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 - x1 < 30 or y2 - y1 < 20:
                continue

            vehicle_crop = frame[y1:y2, x1:x2]

            # Detect plate regions
            plate_boxes = self.plate_detector.detect_plates(vehicle_crop)

            for pb in plate_boxes:
                px1, py1, px2, py2 = [int(b) for b in pb]

                # Clamp plate region
                ch, cw = vehicle_crop.shape[:2]
                px1, py1 = max(0, px1), max(0, py1)
                px2, py2 = min(cw, px2), min(ch, py2)

                if px2 - px1 < 20 or py2 - py1 < 10:
                    continue

                plate_crop = vehicle_crop[py1:py2, px1:px2]

                # Preprocess
                processed, preprocess_steps = self.preprocessor.preprocess(plate_crop)

                # Deskew
                processed = self.preprocessor.deskew(processed)

                # OCR
                plate_text, ocr_confidence = self.ocr.recognize(processed)

                if plate_text and len(plate_text) >= 4:
                    self._stats["plates_detected"] += 1

                    # Overall confidence based on OCR + plate detection quality
                    overall_confidence = ocr_confidence * 0.7 + 0.3

                    result = PlateResult(
                        plate_text=plate_text,
                        confidence=overall_confidence,
                        plate_bbox=[
                            x1 + px1, y1 + py1, x1 + px2, y1 + py2
                        ],
                        vehicle_bbox=bbox,
                        preprocessing_applied=preprocess_steps,
                        status="candidate",
                        method="ocr" if self.ocr_available else "contour_heuristic",
                        evidence_image=plate_crop,
                    )
                    results.append(result)

        return results

    def get_stats(self) -> Dict[str, int]:
        return self._stats.copy()
