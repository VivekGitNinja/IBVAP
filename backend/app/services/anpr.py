"""Automatic Number Plate Recognition (ANPR) service.

Handles plate localization from vehicle detections (contour heuristic or ONNX model),
OCR processing (PaddleOCR/pytesseract if present, or graceful UNAVAILABLE degradation),
and Indian license plate pattern matching.
"""

from __future__ import annotations
import logging
import os
import re
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)

INDIAN_PLATE_PATTERN = re.compile(r"^[A-Z]{2}\s*\d{1,2}\s*[A-Z]{0,3}\s*\d{4}$")


class ANPREngine:
    """Production-grade ANPR engine with graceful degradation."""

    def __init__(self, plate_model_path: Optional[str] = None):
        self.plate_model_path = plate_model_path or "models/plate_detect.onnx"
        self._ocr_checked = False
        self._ocr_backend: Optional[str] = None
        self._ocr_engine: Any = None
        self._unavailable_reason: Optional[str] = None

    def check_ocr_availability(self) -> Tuple[bool, str]:
        """Check if PaddleOCR or pytesseract is installed and usable."""
        if self._ocr_checked:
            if self._ocr_backend:
                return True, f"Ready ({self._ocr_backend})"
            return False, self._unavailable_reason or "OCR unavailable"

        self._ocr_checked = True

        # Check PaddleOCR
        try:
            from paddleocr import PaddleOCR  # type: ignore
            self._ocr_engine = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            self._ocr_backend = "PaddleOCR"
            logger.info("ANPR OCR backend initialized: PaddleOCR")
            return True, "Ready (PaddleOCR)"
        except (ImportError, Exception) as e:
            logger.debug(f"PaddleOCR not available: {e}")

        # Check pytesseract
        try:
            import pytesseract  # type: ignore
            try:
                _ = pytesseract.get_tesseract_version()
                self._ocr_engine = pytesseract
                self._ocr_backend = "pytesseract"
                logger.info("ANPR OCR backend initialized: pytesseract")
                return True, "Ready (pytesseract)"
            except Exception as e:
                self._unavailable_reason = f"pytesseract installed but binary missing: {e}"
                logger.warning(f"ANPR UNAVAILABLE: {self._unavailable_reason}")
                return False, self._unavailable_reason
        except ImportError:
            pass

        self._unavailable_reason = "No OCR engine (PaddleOCR or pytesseract) installed in environment."
        logger.warning(f"ANPR UNAVAILABLE: {self._unavailable_reason}")
        return False, self._unavailable_reason

    def localize_plate(self, vehicle_crop: np.ndarray) -> Tuple[np.ndarray, Optional[Dict[str, float]]]:
        """Localize plate within a vehicle image crop.
        
        Uses morphological filtering and contour analysis (aspect ratio 2.0 - 5.5).
        Returns cropped plate image and relative bounding box [x1, y1, x2, y2].
        """
        vh, vw = vehicle_crop.shape[:2]
        if vh < 20 or vw < 40:
            return vehicle_crop, None

        # Check lower half of vehicle where plates are mounted
        roi_y1 = int(vh * 0.35)
        roi = vehicle_crop[roi_y1:, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi

        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(gray)

        # Morphological gradient to highlight high-frequency text/plate boundaries
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        morph = cv2.morphologyEx(contrast, cv2.MORPH_GRADIENT, kernel)
        _, thresh = cv2.threshold(morph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_rect = None
        best_score = -1.0

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0:
                continue
            aspect = float(w) / float(h)
            area = w * h
            # Standard vehicle plates have aspect ratio between 2.0 and 5.5
            if 1.8 <= aspect <= 5.8 and 400 <= area <= (vw * vh * 0.3):
                # Score based on how close aspect ratio is to typical 3.5
                score = 1.0 - abs(aspect - 3.5) / 3.5
                if score > best_score:
                    best_score = score
                    best_rect = (x, y + roi_y1, w, h)

        if best_rect:
            bx, by, bw, bh = best_rect
            # Add small padding
            pad_x = int(bw * 0.05)
            pad_y = int(bh * 0.08)
            px1 = max(0, bx - pad_x)
            py1 = max(0, by - pad_y)
            px2 = min(vw, bx + bw + pad_x)
            py2 = min(vh, by + bh + pad_y)
            plate_crop = vehicle_crop[py1:py2, px1:px2]
            rel_bbox = {
                "x1": round(px1 / vw, 4),
                "y1": round(py1 / vh, 4),
                "x2": round(px2 / vw, 4),
                "y2": round(py2 / vh, 4),
            }
            return plate_crop, rel_bbox

        # Default fallback: bottom 35% of vehicle crop
        return roi, {"x1": 0.0, "y1": 0.35, "x2": 1.0, "y2": 1.0}

    def read_plate_text(self, plate_crop: np.ndarray) -> Tuple[Optional[str], float]:
        """Perform OCR on plate crop.
        
        Returns (sanitized_plate_text, confidence) or (None, 0.0) if unavailable.
        """
        available, reason = self.check_ocr_availability()
        if not available:
            logger.debug(f"Skipping plate OCR: {reason}")
            return None, 0.0

        raw_text = ""
        conf = 0.5

        if self._ocr_backend == "PaddleOCR":
            try:
                results = self._ocr_engine.ocr(plate_crop, cls=False)
                if results and results[0]:
                    lines = [line[1][0] for line in results[0] if line[1]]
                    scores = [line[1][1] for line in results[0] if line[1]]
                    raw_text = " ".join(lines)
                    if scores:
                        conf = float(sum(scores) / len(scores))
            except Exception as e:
                logger.warning(f"PaddleOCR execution error: {e}")
                return None, 0.0

        elif self._ocr_backend == "pytesseract":
            try:
                import pytesseract  # type: ignore
                gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop
                resized = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                data = pytesseract.image_to_data(resized, output_type=pytesseract.Output.DICT, config="--psm 7")
                texts = []
                confs = []
                for i, text in enumerate(data.get("text", [])):
                    if text.strip():
                        texts.append(text.strip())
                        c = float(data.get("conf", [0])[i])
                        if c > 0:
                            confs.append(c / 100.0)
                raw_text = "".join(texts).strip()
                if not raw_text:
                    raw_text = pytesseract.image_to_string(resized, config="--psm 7").strip()
                    conf = 0.75
                elif confs:
                    conf = float(sum(confs) / len(confs))
            except Exception as e:
                logger.warning(f"pytesseract execution error: {e}")
                return None, 0.0

        if not raw_text:
            return None, 0.0

        # Sanitize text
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        if len(cleaned) < 3:
            return None, 0.0

        # Boost confidence if matches Indian plate format
        if INDIAN_PLATE_PATTERN.match(cleaned):
            conf = min(1.0, conf + 0.15)

        return cleaned, round(conf, 3)

    def process_frame_vehicles(
        self,
        frame: np.ndarray,
        detections: list,
        job_id: Optional[int] = None,
        frame_index: int = 0,
        timestamp_ms: float = 0.0,
        db_session: Any = None,
    ) -> list:
        """Inspect vehicle detections, extract plates, and save PlateRead records."""
        vehicle_classes = {"car", "truck", "bus", "motorcycle", "motorbike", "vehicle", "motion"}
        plate_reads = []

        h, w = frame.shape[:2]

        for det in detections:
            class_name = getattr(det, "class_name", "").lower()
            if class_name not in vehicle_classes:
                continue

            raw_bbox = getattr(det, "bbox", (0, 0, w, h))
            if isinstance(raw_bbox, dict):
                x1 = int(raw_bbox.get("x1", 0.0) * (w if raw_bbox.get("x1", 0.0) <= 1.0 else 1))
                y1 = int(raw_bbox.get("y1", 0.0) * (h if raw_bbox.get("y1", 0.0) <= 1.0 else 1))
                x2 = int(raw_bbox.get("x2", 1.0) * (w if raw_bbox.get("x2", 1.0) <= 1.0 else 1))
                y2 = int(raw_bbox.get("y2", 1.0) * (h if raw_bbox.get("y2", 1.0) <= 1.0 else 1))
            elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4:
                x1, y1, x2, y2 = [int(v) for v in raw_bbox]
            else:
                x1, y1, x2, y2 = 0, 0, w, h

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(x1 + 1, min(w, x2))
            y2 = max(y1 + 1, min(h, y2))

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            plate_crop, rel_bbox = self.localize_plate(crop)
            text, conf = self.read_plate_text(plate_crop)

            if text:
                # Stamp detection metadata
                det_metadata = getattr(det, "metadata", {}) or {}
                det_metadata["plate_text"] = text
                det_metadata["plate_conf"] = conf
                if rel_bbox:
                    det_metadata["plate_bbox"] = rel_bbox
                det.metadata = det_metadata

                if db_session:
                    try:
                        from backend.app.models.plate_read import PlateRead
                        record = PlateRead(
                            job_id=job_id,
                            detection_id=getattr(det, "id", None),
                            camera_id=None,
                            plate_text=text,
                            confidence=conf,
                            frame_index=frame_index,
                            timestamp_ms=timestamp_ms,
                            bbox=rel_bbox or {},
                            method=self._ocr_backend or "contour_ocr",
                        )
                        db_session.add(record)
                        plate_reads.append(record)
                    except Exception as e:
                        logger.error(f"Failed to persist PlateRead record: {e}")

        return plate_reads


anpr_engine = ANPREngine()
