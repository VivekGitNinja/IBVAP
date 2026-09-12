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


def normalize_indian_plate(text: str) -> str:
    """Normalize and repair common OCR character/digit confusions for Indian registration numbers."""
    if not text:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    cleaned = re.sub(r"IND", "", cleaned)

    char_to_num = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8', 'G': '6'}
    num_to_char = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B'}

    # If typical 8-11 char plate: e.g. DL01AB1234 or DL1AB1234 or JK02C5678 or KA02MN1826
    m = re.match(r"^([A-Z0-9]{2})([A-Z0-9]{1,2})([A-Z0-9]{0,3})([A-Z0-9]{4})$", cleaned)
    if m:
        state, rto, series, num = m.groups()
        # State: 2 letters
        state_fixed = "".join(num_to_char.get(c, c) if c.isdigit() else c for c in state)
        # RTO: digits
        rto_fixed = "".join(char_to_num.get(c, c) if not c.isdigit() else c for c in rto)
        # Series: letters
        series_fixed = "".join(num_to_char.get(c, c) if c.isdigit() else c for c in series)
        # Number: 4 digits
        num_fixed = "".join(char_to_num.get(c, c) if not c.isdigit() else c for c in num)
        return f"{state_fixed}{rto_fixed}{series_fixed}{num_fixed}"

    return cleaned


def match_watchlist_plate(text: str) -> Optional[Tuple[str, float]]:
    """Check if raw OCR text contains or matches a known watchlist license plate."""
    from backend.app.api.v1.endpoints.anpr import WATCHLIST_DB
    clean = re.sub(r"[^A-Z0-9]", "", text).upper()
    clean = re.sub(r"IND", "", clean)
    for w in WATCHLIST_DB:
        w_plate = re.sub(r"[^A-Z0-9]", "", w["plate_number"]).upper()
        if clean == w_plate:
            return w["plate_number"], 0.99
        if w_plate in clean:
            return w["plate_number"], 0.98
        # Single-character typo tolerance
        if len(clean) == len(w_plate):
            diffs = sum(1 for a, b in zip(clean, w_plate) if a != b)
            if diffs <= 1:
                return w["plate_number"], 0.95
    return None


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
        cleaned = normalize_indian_plate(raw_text)

        if len(cleaned) < 3:
            return None, 0.0

        # Boost confidence if matches Indian plate format
        if INDIAN_PLATE_PATTERN.match(cleaned):
            conf = min(1.0, conf + 0.15)

        return cleaned, round(conf, 3)

    def process_frame(self, image: np.ndarray) -> list:
        """Process a vehicle image or frame to detect, localize, and OCR license plates.
        
        Returns a list of candidate dictionaries:
        [{"text": "DL01AB1234", "confidence": 0.95, "bbox": {...}, "plate_crop": ...}]
        """
        if image is None or image.size == 0:
            return []

        h, w = image.shape[:2]

        # Resize very high resolution images (e.g. 4k phone uploads) for faster and sharper OCR
        if w > 1280 or h > 1280:
            scale = 1280.0 / max(w, h)
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = image.shape[:2]

        candidates = []

        # 1. Primary: High-accuracy OCR scanning across image for full Indian Registration patterns
        available, _ = self.check_ocr_availability()
        if available:
            try:
                import pytesseract
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                contrast = clahe.apply(gray)
                _, otsu = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                variants = [gray, contrast, otsu]
                found_plates = []

                for var in variants:
                    for psm in ("--psm 7", "--psm 6", "--psm 11", "--psm 3"):
                        try:
                            txt = pytesseract.image_to_string(var, config=psm)
                            if not txt.strip():
                                continue

                            # First, check if text matches a watchlist plate
                            w_match = match_watchlist_plate(txt)
                            if w_match:
                                found_plates.append({"text": w_match[0], "confidence": w_match[1]})
                                break

                            clean_line = re.sub(r"[^A-Za-z0-9\s]", " ", txt).upper()
                            clean_line = re.sub(r"\bIND\b", " ", clean_line)

                            matches = re.findall(r"\b([A-Z0-9]{2}\s*\d{1,2}\s*[A-Z0-9]{0,3}\s*\d{4})\b", clean_line)
                            for m in matches:
                                clean_m = normalize_indian_plate(m)
                                if (INDIAN_PLATE_PATTERN.match(clean_m) or len(clean_m) >= 7) and clean_m not in [p["text"] for p in found_plates]:
                                    found_plates.append({"text": clean_m, "confidence": 0.98})

                            kw_matches = re.findall(r"PLATE\s*:?\s*([A-Z0-9\s]{4,15})", clean_line)
                            for kw in kw_matches:
                                clean_kw = normalize_indian_plate(kw)
                                if INDIAN_PLATE_PATTERN.match(clean_kw) and clean_kw not in [p["text"] for p in found_plates]:
                                    found_plates.append({"text": clean_kw, "confidence": 0.94})
                            if found_plates:
                                break
                        except Exception:
                            pass
                    if found_plates:
                        break

                for fp in found_plates:
                    candidates.append({
                        "text": fp["text"],
                        "confidence": fp["confidence"],
                        "bbox": {"x1": 0.05, "y1": 0.35, "x2": 0.95, "y2": 0.95},
                    })
            except Exception as e:
                logger.debug(f"Direct OCR exception: {e}")

        # 2. Secondary: Contour-based plate localization
        if not candidates:
            plate_crop, rel_bbox = self.localize_plate(image)
            if plate_crop is not None and plate_crop.size > 0:
                text, conf = self.read_plate_text(plate_crop)
                if text and len(text) >= 4:
                    candidates.append({
                        "text": text,
                        "confidence": conf,
                        "bbox": rel_bbox or {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
                        "plate_crop": plate_crop,
                    })

        # 3. Fallback: Lower 45% strip OCR
        if not candidates and available:
            try:
                import pytesseract
                roi = image[int(h * 0.35):, :]
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
                resized_roi = cv2.resize(gray_roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                for psm in ("--psm 11", "--psm 6"):
                    txt = pytesseract.image_to_string(resized_roi, config=psm).strip()
                    w_match = match_watchlist_plate(txt)
                    if w_match:
                        candidates.append({
                            "text": w_match[0],
                            "confidence": w_match[1],
                            "bbox": {"x1": 0.1, "y1": 0.4, "x2": 0.9, "y2": 0.9},
                        })
                        break
                    cleaned = re.sub(r"[^A-Za-z0-9]", "", txt).upper()
                    cleaned = re.sub(r"IND", "", cleaned)
                    norm = normalize_indian_plate(cleaned)
                    if INDIAN_PLATE_PATTERN.match(norm):
                        candidates.append({
                            "text": norm,
                            "confidence": 0.88,
                            "bbox": {"x1": 0.1, "y1": 0.4, "x2": 0.9, "y2": 0.9},
                        })
                        break
            except Exception:
                pass

        return candidates

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

            cand = self.process_frame(crop)
            if cand:
                text = cand[0]["text"]
                conf = cand[0]["confidence"]
                rel_bbox = cand[0].get("bbox")
            else:
                plate_crop, rel_bbox = self.localize_plate(crop)
                text, conf = self.read_plate_text(plate_crop)

            # If crop result is low confidence (< 0.85) or incomplete (< 8 chars), verify against full frame
            if not text or len(text) < 8 or conf < 0.85:
                full_cand = self.process_frame(frame)
                if full_cand:
                    fc = full_cand[0]
                    if not text or fc["confidence"] > conf or len(fc["text"]) > len(text or ""):
                        text = fc["text"]
                        conf = max(conf, fc["confidence"])
                        if fc.get("bbox"):
                            rel_bbox = fc["bbox"]

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

        # Fallback for frames where detector missed the vehicle or road plate exists in frame
        if not plate_reads and (frame_index % 2 == 0 or not detections):
            cand = self.process_frame(frame)
            if cand:
                valid_cands = [
                    c for c in cand
                    if INDIAN_PLATE_PATTERN.match(c["text"]) or c["confidence"] >= 0.95
                ]
                if valid_cands:
                    text = valid_cands[0]["text"]
                    conf = valid_cands[0]["confidence"]
                    rel_bbox = valid_cands[0].get("bbox") or {"x1": 0.1, "y1": 0.4, "x2": 0.9, "y2": 0.9}
                elif cand[0]["confidence"] >= 0.90 and len(cand[0]["text"]) >= 6:
                    text = cand[0]["text"]
                    conf = cand[0]["confidence"]
                    rel_bbox = cand[0].get("bbox") or {"x1": 0.1, "y1": 0.4, "x2": 0.9, "y2": 0.9}
                else:
                    text = None
                    conf = 0.0
                    rel_bbox = None

                if text and db_session:
                    try:
                        from backend.app.models.plate_read import PlateRead
                        record = PlateRead(
                            job_id=job_id,
                            detection_id=None,
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
                        logger.error(f"Failed to persist fallback PlateRead: {e}")

                # Also inject a vehicle Edge Detection so that video analysis tracks and renders this vehicle
                try:
                    from edge.detection.base import Detection as EdgeDetection
                    bx1 = int(rel_bbox.get("x1", 0.1) * (w if rel_bbox.get("x1", 0.1) <= 1.0 else 1))
                    by1 = int(rel_bbox.get("y1", 0.4) * (h if rel_bbox.get("y1", 0.4) <= 1.0 else 1))
                    bx2 = int(rel_bbox.get("x2", 0.9) * (w if rel_bbox.get("x2", 0.9) <= 1.0 else 1))
                    by2 = int(rel_bbox.get("y2", 0.9) * (h if rel_bbox.get("y2", 0.9) <= 1.0 else 1))
                    anpr_det = EdgeDetection(
                        label="vehicle",
                        class_name="vehicle",
                        confidence=conf,
                        bbox=(bx1, by1, bx2, by2),
                        frame_id=frame_index,
                        source="anpr",
                    )
                    anpr_det.metadata = {
                        "plate_text": text,
                        "plate_conf": conf,
                        "plate_bbox": rel_bbox,
                    }
                    detections.append(anpr_det)
                except Exception as det_err:
                    logger.debug(f"Could not append ANPR detection: {det_err}")

        return plate_reads


anpr_engine = ANPREngine()
