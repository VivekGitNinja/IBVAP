"""Face detection, recognition, privacy blurring, and watchlist matching service."""

from __future__ import annotations
import logging
import os
from typing import Optional, Tuple, List, Dict, Any
import cv2
import numpy as np
from sqlalchemy.orm import Session

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

STORAGE_FACES_DIR = "storage/faces"
YUNET_MODEL_PATH = "models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL_PATH = "models/face_recognition_sface_2021dec.onnx"


class FaceService:
    """Production face intelligence service with OpenCV YuNet, Haar fallback, and SFace recognition."""

    def __init__(self):
        os.makedirs(STORAGE_FACES_DIR, exist_ok=True)
        self._detector = None
        self._haar_detector = None
        self._detector_type = "none"
        self._recognition_checked = False
        self._recognition_available = False
        self._recognition_backend = "none"
        self._recognition_reason = ""
        self._recognizer = None
        self._init_detector()

    def _init_detector(self):
        """Initialize YuNet if onnx exists, and ensure Haar Cascade is available."""
        haar_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if os.path.exists(haar_path):
            try:
                self._haar_detector = cv2.CascadeClassifier(haar_path)
            except Exception as e:
                logger.warning(f"Failed to load Haar Cascade: {e}")

        if os.path.exists(YUNET_MODEL_PATH):
            try:
                self._detector = cv2.FaceDetectorYN.create(
                    model=YUNET_MODEL_PATH,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.5,
                    nms_threshold=0.3,
                    top_k=5000,
                )
                self._detector_type = "YuNet"
                logger.info("Face detector initialized with YuNet ONNX")
                return
            except Exception as e:
                logger.warning(f"Failed to load YuNet ONNX: {e}")

        if self._haar_detector is not None:
            self._detector = self._haar_detector
            self._detector_type = "HaarCascade"
            logger.info("Face detector initialized with OpenCV Haar Cascade fallback")
        else:
            self._detector_type = "none"
            logger.warning("No face detector backend available")

    def check_recognition_availability(self) -> Tuple[bool, str]:
        """Check if OpenCV SFace or deep face recognition library is available."""
        if self._recognition_checked:
            return self._recognition_available, self._recognition_reason

        self._recognition_checked = True

        # 1. Primary: OpenCV SFace (cv2.FaceRecognizerSF)
        if os.path.exists(SFACE_MODEL_PATH) and hasattr(cv2, "FaceRecognizerSF"):
            try:
                self._recognizer = cv2.FaceRecognizerSF.create(model=SFACE_MODEL_PATH, config="")
                self._recognition_backend = "SFace"
                self._recognition_available = True
                self._recognition_reason = "Ready (OpenCV SFace)"
                logger.info("Face recognition backend initialized: OpenCV SFace")
                return True, self._recognition_reason
            except Exception as e:
                logger.warning(f"Failed to load OpenCV SFace ONNX: {e}")

        # 2. Secondary: insightface (optional)
        try:
            import insightface  # type: ignore
            app = insightface.app.FaceAnalysis(name="buffalo_s", root="models/")
            app.prepare(ctx_id=-1, det_size=(320, 320))
            self._recognizer = app
            self._recognition_backend = "insightface"
            self._recognition_available = True
            self._recognition_reason = "Ready (insightface/ArcFace)"
            logger.info("Face recognition backend initialized: insightface")
            return True, self._recognition_reason
        except (ImportError, Exception):
            pass

        self._recognition_available = False
        self._recognition_reason = "Face recognition UNAVAILABLE: SFace ONNX model or insightface not installed."
        logger.info(self._recognition_reason)
        return False, self._recognition_reason

    def detect_faces(self, frame: np.ndarray, detections: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Detect faces in a BGR frame. Returns list of face dicts with normalized bbox."""
        h, w = frame.shape[:2]
        faces = []

        if self._detector_type == "YuNet" and self._detector is not None:
            try:
                self._detector.setInputSize((w, h))
                _, detected = self._detector.detect(frame)
                if detected is not None:
                    for d in detected:
                        fx, fy, fw, fh = d[:4]
                        conf = float(d[14]) if len(d) > 14 else 0.8
                        x1 = max(0.0, float(fx) / w)
                        y1 = max(0.0, float(fy) / h)
                        x2 = min(1.0, float(fx + fw) / w)
                        y2 = min(1.0, float(fy + fh) / h)
                        faces.append({
                            "bbox": {"x1": round(x1, 4), "y1": round(y1, 4), "x2": round(x2, 4), "y2": round(y2, 4)},
                            "confidence": round(conf, 3),
                            "crop_coords": (int(fx), int(fy), int(fw), int(fh)),
                            "raw_face": d,
                        })
            except Exception as e:
                logger.error(f"YuNet detection error: {e}")

        elif self._detector_type == "HaarCascade" and self._detector is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
                detected = self._detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                )
                for (fx, fy, fw, fh) in detected:
                    x1 = max(0.0, float(fx) / w)
                    y1 = max(0.0, float(fy) / h)
                    x2 = min(1.0, float(fx + fw) / w)
                    y2 = min(1.0, float(fy + fh) / h)
                    faces.append({
                        "bbox": {"x1": round(x1, 4), "y1": round(y1, 4), "x2": round(x2, 4), "y2": round(y2, 4)},
                        "confidence": 0.85,
                        "crop_coords": (fx, fy, fw, fh),
                    })
            except Exception as e:
                logger.error(f"Haar detection error: {e}")

        # If primary detector didn't detect faces on synthetic/low-res streams, check head regions of person/motion detections
        if len(faces) == 0 and detections:
            for det in detections:
                cname = getattr(det, "class_name", "").lower()
                if cname not in {"person", "motion"}:
                    continue
                raw_bbox = getattr(det, "bbox", (0, 0, w, h))
                if isinstance(raw_bbox, dict):
                    bx1 = int(raw_bbox.get("x1", 0.0) * (w if raw_bbox.get("x1", 0.0) <= 1.0 else 1))
                    by1 = int(raw_bbox.get("y1", 0.0) * (h if raw_bbox.get("y1", 0.0) <= 1.0 else 1))
                    bx2 = int(raw_bbox.get("x2", 1.0) * (w if raw_bbox.get("x2", 1.0) <= 1.0 else 1))
                    by2 = int(raw_bbox.get("y2", 1.0) * (h if raw_bbox.get("y2", 1.0) <= 1.0 else 1))
                elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4:
                    bx1, by1, bx2, by2 = [int(v) for v in raw_bbox]
                else:
                    bx1, by1, bx2, by2 = 0, 0, w, h

                bh = max(1, by2 - by1)
                bw = max(1, bx2 - bx1)
                if bh < 25 or bw < 16:
                    continue

                # Head occupies the upper ~35% of a standing person
                head_h = max(16, int(bh * 0.35))
                hx1 = max(0, min(w - 1, bx1))
                hy1 = max(0, min(h - 1, by1))
                hx2 = max(hx1 + 1, min(w, bx2))
                hy2 = max(hy1 + 1, min(h, by1 + head_h))

                hcrop = frame[hy1:hy2, hx1:hx2]
                if hcrop.size > 0 and (hx2 - hx1) >= 16 and (hy2 - hy1) >= 16:
                    gray_hc = cv2.cvtColor(hcrop, cv2.COLOR_BGR2GRAY) if len(hcrop.shape) == 3 else hcrop
                    if float(np.std(gray_hc)) > 10.0:
                        faces.append({
                            "bbox": {
                                "x1": round(hx1 / w, 4),
                                "y1": round(hy1 / h, 4),
                                "x2": round(hx2 / w, 4),
                                "y2": round(hy2 / h, 4),
                            },
                            "confidence": 0.80,
                            "crop_coords": (hx1, hy1, hx2 - hx1, hy2 - hy1),
                            "raw_face": None,
                        })

        return faces

    def extract_embedding(self, face_image: np.ndarray, raw_face: Optional[Any] = None, full_frame: Optional[np.ndarray] = None) -> Optional[List[float]]:
        """Extract a 128-dim embedding vector using SFace (or 512-dim using insightface)."""
        avail, reason = self.check_recognition_availability()
        if not avail or self._recognizer is None:
            logger.debug(f"Skipping face embedding: {reason}")
            return None

        if getattr(self, "_recognition_backend", "") == "SFace":
            try:
                aligned = None
                if raw_face is not None and full_frame is not None:
                    try:
                        aligned = self._recognizer.alignCrop(full_frame, raw_face)
                    except Exception:
                        aligned = None

                if aligned is None and face_image is not None and face_image.size > 0:
                    aligned = cv2.resize(face_image, (112, 112), interpolation=cv2.INTER_LINEAR)

                if aligned is not None:
                    feat = self._recognizer.feature(aligned)
                    if feat is not None:
                        vec = feat.flatten()
                        norm = np.linalg.norm(vec)
                        if norm > 0:
                            vec = vec / norm
                        return [round(float(x), 6) for x in vec]
            except Exception as e:
                logger.warning(f"SFace feature extraction error: {e}")
                return None

        elif getattr(self, "_recognition_backend", "") == "insightface":
            try:
                faces = self._recognizer.get(face_image)
                if faces and hasattr(faces[0], "normed_embedding"):
                    emb = faces[0].normed_embedding
                    return [round(float(x), 6) for x in emb]
            except Exception as e:
                logger.warning(f"insightface embedding error: {e}")

        return None

    def enroll_face(self, image: np.ndarray) -> Tuple[Optional[List[float]], Optional[str]]:
        """Detect the largest face in an image and extract its 128-dim embedding.
        
        Returns (embedding, None) or (None, error_message).
        """
        avail, reason = self.check_recognition_availability()
        if not avail or self._recognizer is None:
            return None, f"Face recognition unavailable: {reason}"

        if image is None or image.size == 0:
            return None, "Empty image provided"

        h, w = image.shape[:2]
        aligned = None

        # 1. Try YuNet
        if self._detector_type == "YuNet" and self._detector is not None:
            try:
                self._detector.setInputSize((w, h))
                _, detected = self._detector.detect(image)
                if detected is not None and len(detected) > 0:
                    largest_face = max(detected, key=lambda d: d[2] * d[3])
                    aligned = self._recognizer.alignCrop(image, largest_face)
            except Exception as e:
                logger.debug(f"YuNet enroll detect error: {e}")

        # 2. Try Haar Cascade fallback
        if aligned is None and self._haar_detector is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            haar_faces = self._haar_detector.detectMultiScale(gray, 1.1, 3)
            if len(haar_faces) > 0:
                hx, hy, hw, hh = max(haar_faces, key=lambda r: r[2] * r[3])
                aligned = cv2.resize(image[hy:hy+hh, hx:hx+hw], (112, 112))

        # 3. If image itself is already cropped face proportions (aspect 0.6 - 1.5)
        if aligned is None and 0.6 <= (w / max(1, h)) <= 1.5 and min(w, h) >= 30:
            # Check if there is basic variation (not a solid flat background)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            if float(np.std(gray)) > 15.0:
                aligned = cv2.resize(image, (112, 112))

        if aligned is None:
            return None, "no detectable face"

        try:
            feat = self._recognizer.feature(aligned)
            if feat is not None:
                vec = feat.flatten()
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                return [round(float(x), 6) for x in vec], None
        except Exception as e:
            return None, f"Feature extraction failed: {e}"

        return None, "no detectable face"

    def match_watchlist(self, embedding: Optional[List[float]], db: Session) -> Optional[Tuple[Any, float]]:
        """Compute cosine similarity against enrolled watchlist faces."""
        if embedding is None:
            return None

        from backend.app.models.watchlist import Watchlist
        enrolled = db.query(Watchlist).filter(Watchlist.embedding.isnot(None)).all()
        if not enrolled:
            return None

        v1 = np.array(embedding, dtype=np.float32)
        norm1 = np.linalg.norm(v1)
        if norm1 == 0:
            return None

        best_match = None
        best_sim = -1.0

        for subject in enrolled:
            if not subject.embedding:
                continue
            v2 = np.array(subject.embedding, dtype=np.float32)
            norm2 = np.linalg.norm(v2)
            if norm2 == 0:
                continue
            sim = float(np.dot(v1, v2) / (norm1 * norm2))
            if sim > best_sim:
                best_sim = sim
                best_match = subject

        if best_match and best_sim >= settings.face_match_threshold:
            return best_match, round(best_sim, 4)

        return None

    def apply_face_blur(self, frame: np.ndarray, faces: List[Dict[str, Any]]) -> np.ndarray:
        """Apply Gaussian blur on detected face bounding boxes to preserve privacy."""
        h, w = frame.shape[:2]
        blurred = frame.copy()

        for face in faces:
            bbox = face.get("bbox", {})
            x1 = int(bbox.get("x1", 0.0) * w)
            y1 = int(bbox.get("y1", 0.0) * h)
            x2 = int(bbox.get("x2", 1.0) * w)
            y2 = int(bbox.get("y2", 1.0) * h)

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(x1 + 1, min(w, x2))
            y2 = max(y1 + 1, min(h, y2))

            crop = blurred[y1:y2, x1:x2]
            if crop.shape[0] < 4 or crop.shape[1] < 4:
                continue

            # Gaussian blur with large kernel
            ksize = (31, 31)
            blurred_crop = cv2.GaussianBlur(crop, ksize, 15)
            blurred[y1:y2, x1:x2] = blurred_crop

        return blurred


face_service = FaceService()
