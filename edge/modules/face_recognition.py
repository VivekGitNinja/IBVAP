"""
Face Recognition Watchlist Module
==================================

Privacy-preserving face recognition for border surveillance:
1. Detect faces (InsightFace RetinaFace or OpenCV Haar/DNN fallback)
2. Extract ArcFace embeddings
3. Match against watchlist gallery (cosine similarity)
4. Store unknown faces for later review
5. All matches are CANDIDATE-ONLY — require human verification

IMPORTANT: This is NOT autonomous identification.
All outputs are decision-support only with confidence scores.

Usage:
    from edge.modules.face_recognition import FaceRecognitionModule

    fr = FaceRecognitionModule()
    results = fr.process_frame(frame)
    for r in results:
        if r.is_watchlist_match:
            print(f"CANDIDATE MATCH: {r.identity} (confidence: {r.similarity:.2f})")

Fallback chain:
    InsightFace (buffalo_l) → InsightFace (buffalo_sc) → RetinaFace → OpenCV DNN → Haar Cascade
    ArcFace embedding → random projection hash → skip

License:
    InsightFace: MIT (for non-commercial research)
    OpenCV models: Apache 2.0
"""

from __future__ import annotations
import os
import time
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Thresholds
MATCH_THRESHOLD = 0.45  # Cosine similarity threshold for watchlist match
UNKNOWN_STORE_THRESHOLD = 0.3  # Below this = probably not a face embedding
GALLERY_MAX_SIZE = 10000  # Max unknown faces to store
EMBEDDING_DIM = 512  # ArcFace dimension


@dataclass
class FaceMatch:
    """Result of face recognition on a single face."""
    bbox: List[float] = field(default_factory=lambda: [0, 0, 0, 0])
    confidence: float = 0.0
    embedding: Optional[np.ndarray] = None
    identity: str = "unknown"
    similarity: float = 0.0
    is_watchlist_match: bool = False
    thumbnail: Optional[np.ndarray] = None
    frame_id: int = 0
    method: str = "none"
    face_id: int = 0  # Sequential face ID in this frame

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": [round(b, 1) for b in self.bbox],
            "confidence": round(self.confidence, 3),
            "identity": self.identity,
            "similarity": round(self.similarity, 3),
            "is_watchlist_match": self.is_watchlist_match,
            "face_id": self.face_id,
            "method": self.method,
        }


class EmbeddingGallery:
    """In-memory gallery for face embeddings.

    Stores watchlist embeddings and recent unknown face embeddings.
    Supports cosine similarity search.
    """

    def __init__(self):
        self._watchlist: Dict[str, List[np.ndarray]] = {}  # name -> [embeddings]
        self._unknown_faces: List[Dict[str, Any]] = []  # recent unknown faces
        self._unknown_max = GALLERY_MAX_SIZE

    def add_watchlist(self, name: str, embedding: np.ndarray) -> None:
        """Add an embedding to the watchlist for a named identity."""
        if name not in self._watchlist:
            self._watchlist[name] = []
        self._watchlist[name].append(embedding.astype(np.float32))
        logger.info(f"Added watchlist entry for '{name}' ({len(self._watchlist[name])} embeddings)")

    def load_watchlist_from_dir(self, directory: str) -> int:
        """Load watchlist from a directory structure.

        Expected: directory/<identity_name>/<image_or_npy_files>
        Returns count of embeddings loaded.
        """
        count = 0
        watch_dir = Path(directory)
        if not watch_dir.exists():
            logger.warning(f"Watchlist directory not found: {directory}")
            return 0

        for identity_dir in watch_dir.iterdir():
            if not identity_dir.is_dir():
                continue
            name = identity_dir.name

            for f in identity_dir.iterdir():
                if f.suffix == ".npy":
                    try:
                        emb = np.load(str(f))
                        if emb.ndim == 1:
                            emb = emb.reshape(1, -1)
                        for i in range(emb.shape[0]):
                            self.add_watchlist(name, emb[i])
                            count += 1
                    except Exception as e:
                        logger.warning(f"Failed to load {f}: {e}")
                elif f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                    try:
                        img = cv2.imread(str(f))
                        if img is not None:
                            detector = FaceDetectorAdapter()
                            faces = detector.detect(img)
                            for face in faces:
                                emb = detector.embed(img, face.bbox)
                                if emb is not None:
                                    self.add_watchlist(name, emb)
                                    count += 1
                    except Exception as e:
                        logger.warning(f"Failed to process {f}: {e}")

        logger.info(f"Loaded {count} watchlist embeddings from {directory}")
        return count

    def search(
        self, embedding: np.ndarray, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Search gallery for nearest identities.

        Args:
            embedding: Query embedding (512-dim ArcFace)
            top_k: Number of top matches to return

        Returns:
            List of (identity_name, cosine_similarity) tuples, sorted descending
        """
        if embedding is None or embedding.ndim != 1:
            return []

        embedding = embedding.astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm < 1e-6:
            return []
        embedding_norm = embedding / norm

        matches: List[Tuple[str, float]] = []

        for name, embeddings_list in self._watchlist.items():
            for stored_emb in embeddings_list:
                stored_norm = np.linalg.norm(stored_emb)
                if stored_norm < 1e-6:
                    continue
                similarity = float(np.dot(embedding_norm, stored_emb / stored_norm))
                matches.append((name, similarity))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_k]

    def store_unknown(
        self, embedding: np.ndarray, bbox: List[float],
        thumbnail: Optional[np.ndarray] = None,
        frame_id: int = 0, camera_id: str = "",
    ) -> int:
        """Store an unknown face embedding for later review.

        Returns the ID of the stored face.
        """
        if embedding is None:
            return -1

        face_id = len(self._unknown_faces)
        entry = {
            "id": face_id,
            "embedding": embedding.astype(np.float32),
            "bbox": bbox,
            "timestamp": datetime.utcnow().isoformat(),
            "frame_id": frame_id,
            "camera_id": camera_id,
            "reviewed": False,
        }

        self._unknown_faces.append(entry)

        # Trim if too large
        if len(self._unknown_faces) > self._unknown_max:
            self._unknown_faces = self._unknown_faces[-self._unknown_max:]

        return face_id

    def get_unknown_faces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get stored unknown faces for review (without embeddings)."""
        return [
            {k: v for k, v in f.items() if k != "embedding"}
            for f in self._unknown_faces[-limit:]
        ]

    @property
    def watchlist_size(self) -> int:
        return sum(len(v) for v in self._watchlist.values())

    @property
    def unknown_count(self) -> int:
        return len(self._unknown_faces)

    @property
    def identities(self) -> List[str]:
        return list(self._watchlist.keys())

    def save_gallery(self, path: str) -> None:
        """Save gallery to disk."""
        data = {
            "watchlist": {},
            "unknown_count": len(self._unknown_faces),
        }
        for name, embeddings in self._watchlist.items():
            data["watchlist"][name] = [e.tolist() for e in embeddings]

        with open(path, "w") as f:
            json.dump(data, f)
        logger.info(f"Saved gallery to {path}")

    def load_gallery(self, path: str) -> bool:
        """Load gallery from disk."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for name, embeddings_list in data.get("watchlist", {}).items():
                for emb_list in embeddings_list:
                    self.add_watchlist(name, np.array(emb_list, dtype=np.float32))
            logger.info(f"Loaded gallery from {path}: {self.watchlist_size} watchlist embeddings")
            return True
        except Exception as e:
            logger.warning(f"Failed to load gallery: {e}")
            return False


class FaceDetectorAdapter:
    """Unified face detector with multiple backends.

    Tries: InsightFace → RetinaFace → OpenCV DNN → Haar Cascade
    Also provides embedding extraction when InsightFace is available.
    """

    def __init__(self, preferred: str = "auto"):
        self._backend = None
        self._embedder = None
        self._method = "none"
        self._init_backend(preferred)

    def _init_backend(self, preferred: str) -> None:
        """Initialize the best available face detector."""

        # Try InsightFace (best quality: detection + embedding in one)
        try:
            import insightface
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection", "embedding"],
            )
            app.prepare(ctx_id=0, det_size=(640, 640))

            self._backend = app
            self._embedder = app  # InsightFace does both
            self._method = "insightface"
            logger.info("Loaded InsightFace buffalo_l (detection + ArcFace embedding)")
            return
        except ImportError:
            logger.info("InsightFace not installed, trying buffalo_sc...")
        except Exception as e:
            logger.warning(f"InsightFace buffalo_l failed: {e}")

        # Try InsightFace lightweight
        try:
            import insightface
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(
                name="buffalo_sc",
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection", "embedding"],
            )
            app.prepare(ctx_id=0, det_size=(320, 320))

            self._backend = app
            self._embedder = app
            self._method = "insightface_sc"
            logger.info("Loaded InsightFace buffalo_sc (lightweight)")
            return
        except Exception:
            pass

        # Fallback: OpenCV DNN face detection
        try:
            model_path = "models/opencv_face_detector_uint8.pb"
            config_path = "models/opencv_face_detector.pbtxt"
            if os.path.exists(model_path) and os.path.exists(config_path):
                self._backend = cv2.dnn.readNetFromTensorflow(model_path, config_path)
                self._method = "opencv_dnn"
                logger.info("Loaded OpenCV DNN face detector")
                return
        except Exception:
            pass

        # Final fallback: Haar cascade
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(cascade_path):
            self._backend = cv2.CascadeClassifier(cascade_path)
            self._method = "haar_cascade"
            logger.info("Using Haar cascade face detector (detection only, no embedding)")

    @property
    def method(self) -> str:
        return self._method

    @property
    def is_available(self) -> bool:
        """Whether a face detector backend loaded successfully."""
        return self._method != "none" and self._backend is not None

    @property
    def has_embedding(self) -> bool:
        return self._method in ("insightface", "insightface_sc")

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces in frame.

        Returns list of dicts with keys: bbox, confidence, landmarks (optional)
        """
        if self._method in ("insightface", "insightface_sc"):
            return self._detect_insightface(frame)
        elif self._method == "opencv_dnn":
            return self._detect_dnn(frame)
        elif self._method == "haar_cascade":
            return self._detect_haar(frame)
        return []

    def embed(self, frame: np.ndarray, bbox: List[float]) -> Optional[np.ndarray]:
        """Extract face embedding.

        Returns 512-dim ArcFace embedding, or None if not available.
        """
        if not self.has_embedding or self._embedder is None:
            return None

        try:
            x1, y1, x2, y2 = [int(b) for b in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 - x1 < 20 or y2 - y1 < 20:
                return None

            face_crop = frame[y1:y2, x1:x2]

            # InsightFace can get embedding directly
            faces = self._embedder.get(frame)
            if faces:
                # Find the face that overlaps most with our bbox
                best_face = None
                best_iou = 0
                for face in faces:
                    fb = face.bbox.astype(float).tolist()
                    iou = _iou(bbox, fb)
                    if iou > best_iou:
                        best_iou = iou
                        best_face = face

                if best_face is not None and hasattr(best_face, "embedding"):
                    return best_face.embedding.astype(np.float32)

            return None
        except Exception as e:
            logger.error(f"Embedding extraction error: {e}")
            return None

    def _detect_insightface(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """InsightFace detection."""
        faces = self._backend.get(frame)
        results = []
        for face in faces:
            bbox = face.bbox.astype(float).tolist()
            results.append({
                "bbox": bbox,
                "confidence": float(face.det_score),
                "landmarks": face.landmark.tolist() if hasattr(face, "landmark") else None,
            })
        return results

    def _detect_dnn(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """OpenCV DNN detection."""
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
        )
        self._backend.setInput(blob)
        dets = self._backend.forward()

        results = []
        for i in range(dets.shape[2]):
            conf = float(dets[0, 0, i, 2])
            if conf < 0.5:
                continue
            x1 = int(dets[0, 0, i, 3] * w)
            y1 = int(dets[0, 0, i, 4] * h)
            x2 = int(dets[0, 0, i, 5] * w)
            y2 = int(dets[0, 0, i, 6] * h)
            results.append({"bbox": [float(x1), float(y1), float(x2), float(y2)], "confidence": conf})
        return results

    def _detect_haar(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Haar cascade detection."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = self._backend.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return [{"bbox": [float(x), float(y), float(x + w), float(y + h)], "confidence": 0.7} for (x, y, w, h) in rects]


def _iou(box_a: List[float], box_b: List[float]) -> float:
    """Compute IoU between two boxes [x1,y1,x2,y2]."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / max(union, 1e-6)


class FaceRecognitionModule:
    """Complete face recognition pipeline.

    Combines detection, embedding extraction, and gallery matching.
    All matches are candidate-only — require human verification.

    Usage:
        fr = FaceRecognitionModule()
        fr.load_watchlist("data/watchlist/")
        results = fr.process_frame(frame)
    """

    def __init__(
        self,
        match_threshold: float = MATCH_THRESHOLD,
        store_unknown: bool = True,
    ):
        """
        Args:
            match_threshold: cosine similarity threshold for watchlist match
            store_unknown: whether to store unknown face embeddings
        """
        self.match_threshold = match_threshold
        self.store_unknown = store_unknown
        self.detector = FaceDetectorAdapter()
        self.gallery = EmbeddingGallery()
        self._frame_count = 0
        self._stats = {"faces_detected": 0, "watchlist_matches": 0, "unknown_stored": 0}
        self._fallback_mode = not self.detector.is_available or self.detector.method in ("haar_cascade", "opencv_dnn")

        logger.info(f"Face recognition initialized: method={self.detector.method}, "
                    f"embedding={'yes' if self.detector.has_embedding else 'no'}, "
                    f"fallback={self._fallback_mode}")

    def load_watchlist(self, directory: str) -> int:
        """Load watchlist from directory."""
        return self.gallery.load_watchlist_from_dir(directory)

    def load_gallery_file(self, path: str) -> bool:
        """Load gallery from JSON file."""
        return self.gallery.load_gallery(path)

    def add_watchlist_face(self, name: str, embedding: np.ndarray) -> None:
        """Add a face embedding to the watchlist."""
        self.gallery.add_watchlist(name, embedding)

    def process_frame(
        self, frame: np.ndarray, frame_id: int = 0,
        camera_id: str = "",
    ) -> List[FaceMatch]:
        """Process a frame for face recognition.

        Args:
            frame: BGR image (H, W, 3)
            frame_id: frame sequence number
            camera_id: camera identifier for logging

        Returns:
            List of FaceMatch results
        """
        self._frame_count += 1
        fid = frame_id or self._frame_count

        # Detect faces
        faces = self.detector.detect(frame)
        if not faces:
            return []

        results = []
        for i, face in enumerate(faces):
            bbox = face["bbox"]
            conf = face["confidence"]

            # Extract embedding (if available)
            embedding = self.detector.embed(frame, bbox)

            # Search watchlist
            identity = "unknown"
            similarity = 0.0
            is_match = False

            if embedding is not None:
                matches = self.gallery.search(embedding, top_k=1)
                if matches:
                    top_name, top_sim = matches[0]
                    if top_sim >= self.match_threshold:
                        identity = top_name
                        similarity = top_sim
                        is_match = True
                        self._stats["watchlist_matches"] += 1

            # Store unknown face
            if self.store_unknown and embedding is not None and not is_match:
                self.gallery.store_unknown(
                    embedding, bbox, frame_id=fid, camera_id=camera_id,
                )
                self._stats["unknown_stored"] += 1

            # Extract thumbnail
            x1, y1, x2, y2 = [int(b) for b in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            thumbnail = frame[y1:y2, x1:x2].copy() if x2 > x1 and y2 > y1 else None

            match = FaceMatch(
                bbox=bbox,
                confidence=conf,
                embedding=embedding,
                identity=identity,
                similarity=similarity,
                is_watchlist_match=is_match,
                thumbnail=thumbnail,
                frame_id=fid,
                method=self.detector.method,
                face_id=i,
            )
            results.append(match)
            self._stats["faces_detected"] += 1

        return results

    def draw_results(
        self, frame: np.ndarray, results: List[FaceMatch]
    ) -> np.ndarray:
        """Draw face recognition results on frame.

        - Watchlist matches: RED bounding box with name
        - Unknown faces: CYAN bounding box
        """
        output = frame.copy()
        for r in results:
            x1, y1, x2, y2 = [int(b) for b in r.bbox]

            if r.is_watchlist_match:
                color = (0, 0, 255)  # RED for watchlist
                label = f"WATCHLIST: {r.identity} ({r.similarity:.2f})"
            else:
                color = (255, 200, 0)  # CYAN for unknown
                label = f"Unknown ({r.confidence:.2f})"

            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(output, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(output, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            if r.is_watchlist_match:
                # Draw alert indicator
                cv2.putText(output, "!", (x2 + 5, y1 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        return output

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "gallery_watchlist": self.gallery.watchlist_size,
            "gallery_unknown": self.gallery.unknown_count,
            "identities": self.gallery.identities,
            "method": self.detector.method,
        }

    def get_unknown_faces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unknown faces for operator review."""
        return self.gallery.get_unknown_faces(limit)


# ── Quick test ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

# Module-level singleton
_face_engine = None


def get_face_engine(**kwargs) -> FaceRecognitionModule:
    """Get or create the singleton face recognition module."""
    global _face_engine
    if _face_engine is None:
        _face_engine = FaceRecognitionModule(**kwargs)
    return _face_engine


if __name__ == "__main__":
    fr = FaceRecognitionModule()
    print(f"Face recognition initialized: {fr.get_stats()}")

    # Test with webcam or sample image
    if len(sys.argv) > 1:
        frame = cv2.imread(sys.argv[1])
        if frame is not None:
            results = fr.process_frame(frame)
            print(f"Faces detected: {len(results)}")
            for r in results:
                print(f"  {r.to_dict()}")
            output = fr.draw_results(frame, results)
            cv2.imwrite("/tmp/face_test.jpg", output)
            print("Saved to /tmp/face_test.jpg")
    else:
        print("Usage: python face_recognition.py <image_path>")
