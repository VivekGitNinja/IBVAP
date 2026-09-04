"""
Person Re-Identification (Re-ID) Module
========================================

Uses OSNet (Omni-Scale Network) to extract person re-identification embeddings.
Enables cross-camera person matching without biometric identification.

Architecture:
- OSNet extracts 512-d embeddings from person crops
- Gallery stores recent embeddings (last 30 min) with metadata
- Cosine similarity search for nearest matches
- Cooldown prevents duplicate alerts

This is for TRACKING PERSONS ACROSS CAMERAS, not facial identification.
It matches based on body appearance, gait characteristics, and clothing.

Sources:
- torchreid: https://github.com/KaiyangZhou/deep-person-reid
- OSNet paper: "Omni-Scale Feature Learning for Person Re-Identification" (ICCV 2019)
- License: MIT (torchreid)
"""

import logging
import time
import hashlib
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PersonEmbedding:
    """A person embedding with metadata."""
    embedding: np.ndarray          # 512-d OSNet embedding
    camera_id: str                 # Source camera
    track_id: int                  # Local track ID on source camera
    timestamp: float               # When captured
    bbox: Optional[Tuple] = None   # Bounding box (x1,y1,x2,y2)
    crop: Optional[np.ndarray] = None  # Person crop image
    gallery_id: Optional[str] = None   # Global gallery ID


@dataclass
class CrossCameraMatch:
    """A match between persons across different cameras."""
    query_embedding: PersonEmbedding   # New observation
    match_embedding: PersonEmbedding   # Gallery match
    similarity: float                  # Cosine similarity
    time_gap: float                    # Seconds between observations
    confidence: str                    # HIGH/MEDIUM/LOW


class ReIDGallery:
    """
    In-memory gallery of person embeddings with time-based expiration.
    
    Stores recent embeddings from all cameras for cross-camera matching.
    Does NOT store persistent face data — only body appearance embeddings.
    """
    
    def __init__(self, max_age_seconds: int = 1800, max_entries: int = 10000):
        """
        Args:
            max_age_seconds: How long to keep embeddings (default 30 min)
            max_entries: Maximum gallery size
        """
        self._gallery: List[PersonEmbedding] = []
        self._max_age = max_age_seconds
        self._max_entries = max_entries
        self._stats = {
            "total_adds": 0,
            "total_searches": 0,
            "total_matches": 0,
            "expired": 0,
        }
    
    def add(self, embedding: PersonEmbedding) -> None:
        """Add embedding to gallery."""
        self._gallery.append(embedding)
        self._stats["total_adds"] += 1
        
        # Evict old entries
        self._evict_expired()
        
        # Cap gallery size
        if len(self._gallery) > self._max_entries:
            self._gallery = self._gallery[-self._max_entries:]
    
    def search(
        self,
        query: np.ndarray,
        top_k: int = 5,
        min_similarity: float = 0.5,
        exclude_camera: Optional[str] = None,
        time_window: Optional[float] = None,
    ) -> List[Tuple[PersonEmbedding, float]]:
        """
        Search gallery for similar embeddings.
        
        Args:
            query: Query embedding (512-d)
            top_k: Number of results
            min_similarity: Minimum cosine similarity
            exclude_camera: Don't match from same camera
            time_window: Only match within this time window (seconds)
            
        Returns:
            List of (PersonEmbedding, similarity) sorted by similarity desc
        """
        self._stats["total_searches"] += 1
        self._evict_expired()
        
        if not self._gallery:
            return []
        
        results = []
        now = time.time()
        
        for entry in self._gallery:
            # Skip same camera (we want cross-camera matches)
            if exclude_camera and entry.camera_id == exclude_camera:
                continue
            
            # Time window filter
            if time_window and (now - entry.timestamp) > time_window:
                continue
            
            # Cosine similarity
            sim = self._cosine_similarity(query, entry.embedding)
            
            if sim >= min_similarity:
                results.append((entry, sim))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        if results:
            self._stats["total_matches"] += len(results)
        
        return results[:top_k]
    
    def _evict_expired(self) -> None:
        """Remove embeddings older than max_age."""
        now = time.time()
        before = len(self._gallery)
        self._gallery = [
            e for e in self._gallery
            if (now - e.timestamp) < self._max_age
        ]
        expired = before - len(self._gallery)
        self._stats["expired"] += expired
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def get_stats(self) -> Dict:
        """Get gallery statistics."""
        return {
            **self._stats,
            "gallery_size": len(self._gallery),
            "max_age_seconds": self._max_age,
        }
    
    def clear(self) -> None:
        """Clear the gallery."""
        self._gallery.clear()


class ReIDEngine:
    """
    Person Re-Identification engine.
    
    Extracts appearance embeddings from person crops using OSNet,
    then searches a gallery for cross-camera matches.
    
    Fallback: If torchreid/OSNet is not available, returns deterministic
    hash-based embeddings for demo purposes (clearly labeled as fallback).
    """
    
    def __init__(
        self,
        model_name: str = "osnet_ain_x1_0",
        device: str = "cpu",
        gallery_max_age: int = 1800,
    ):
        self._model_name = model_name
        self._device = device
        self._gallery = ReIDGallery(max_age_seconds=gallery_max_age)
        self._model = None
        self._transform = None
        self._available = False
        self._fallback_mode = False
        self._match_cooldown: Dict[str, float] = {}  # fingerprint -> last_match_time
        self._cooldown_seconds = 60  # Don't re-alert same match within 60s
        
        self._init_model()
    
    def _init_model(self) -> None:
        """Initialize OSNet model with fallback."""
        try:
            import torch
            from torchreid.utils import FeatureExtractor
            
            self._model = FeatureExtractor(
                model_name=self._model_name,
                model_path='',  # Auto-download
                device=self._device
            )
            self._available = True
            self._fallback_mode = False
            logger.info(f"ReID: OSNet ({self._model_name}) loaded on {self._device}")
            
        except ImportError:
            logger.warning("ReID: torchreid not available, using fallback embeddings")
            self._fallback_mode = True
            self._available = True  # Still "available" via fallback
            
        except Exception as e:
            logger.warning(f"ReID: OSNet init failed ({e}), using fallback")
            self._fallback_mode = True
            self._available = True
    
    def extract_embedding(self, person_crop: np.ndarray) -> np.ndarray:
        """
        Extract a 512-d Re-ID embedding from a person crop.
        
        Args:
            person_crop: BGR image crop of a person (H x W x 3)
            
        Returns:
            512-d normalized embedding vector
        """
        if person_crop is None or person_crop.size == 0:
            return np.zeros(512, dtype=np.float32)
        
        if self._fallback_mode:
            return self._fallback_embedding(person_crop)
        
        try:
            import torch
            
            # Preprocess: resize to 256x128 (standard ReID input)
            import cv2
            resized = cv2.resize(person_crop, (128, 256))
            
            # Convert BGR -> RGB -> tensor
            from PIL import Image
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            
            # torchreid expects (1, 3, 256, 128) tensor
            import torchvision.transforms as T
            transform = T.Compose([
                T.Resize((256, 128)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406],
                           std=[0.229, 0.224, 0.225])
            ])
            
            tensor = transform(pil_img).unsqueeze(0).to(self._device)
            
            with torch.no_grad():
                embedding = self._model(tensor)
            
            # Normalize
            embedding = embedding.cpu().numpy().flatten()
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"ReID: Embedding extraction failed ({e})")
            return self._fallback_embedding(person_crop)
    
    def _fallback_embedding(self, person_crop: np.ndarray) -> np.ndarray:
        """
        Deterministic fallback embedding based on visual features.
        
        Uses color histograms + spatial features to create a consistent
        but less accurate embedding. Clearly labeled as DEMO FALLBACK.
        """
        import cv2
        
        try:
            # Resize to standard size
            resized = cv2.resize(person_crop, (128, 256))
            
            # Color histogram (3 channels, 16 bins each = 48 features)
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            h_hist = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
            s_hist = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
            v_hist = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()
            
            # Normalize histograms
            h_hist = h_hist / (h_hist.sum() + 1e-7)
            s_hist = s_hist / (s_hist.sum() + 1e-7)
            v_hist = v_hist / (v_hist.sum() + 1e-7)
            
            # Spatial features: divide into 4x2 grid, compute mean intensity
            h, w = resized.shape[:2]
            spatial = []
            for row in range(2):
                for col in range(4):
                    patch = resized[row*h//2:(row+1)*h//2, col*w//4:(col+1)*w//4]
                    spatial.append(np.mean(patch) / 255.0)
            
            # Combine features
            features = np.concatenate([h_hist, s_hist, v_hist, spatial])
            
            # Pad/truncate to 512 dimensions
            embedding = np.zeros(512, dtype=np.float32)
            embedding[:len(features)] = features[:512]
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
            
        except Exception:
            return np.random.randn(512).astype(np.float32)
    
    def match_person(
        self,
        person_crop: np.ndarray,
        camera_id: str,
        track_id: int,
        bbox: Optional[Tuple] = None,
        min_similarity: float = 0.5,
    ) -> Optional[CrossCameraMatch]:
        """
        Extract embedding and search for cross-camera match.
        
        Args:
            person_crop: Person image crop
            camera_id: Source camera
            track_id: Local track ID
            bbox: Bounding box
            min_similarity: Minimum match threshold
            
        Returns:
            CrossCameraMatch if found, None otherwise
        """
        if not self._available:
            return None
        
        embedding = self.extract_embedding(person_crop)
        
        if np.all(embedding == 0):
            return None
        
        # Search gallery (exclude same camera)
        matches = self._gallery.search(
            query=embedding,
            top_k=1,
            min_similarity=min_similarity,
            exclude_camera=camera_id,
            time_window=600,  # Only match within 10 minutes
        )
        
        if not matches:
            # Add to gallery
            pe = PersonEmbedding(
                embedding=embedding,
                camera_id=camera_id,
                track_id=track_id,
                timestamp=time.time(),
                bbox=bbox,
                crop=person_crop,
            )
            self._gallery.add(pe)
            return None
        
        match_entry, similarity = matches[0]
        
        # Check cooldown
        fingerprint = f"{camera_id}:{track_id}:{match_entry.camera_id}:{match_entry.track_id}"
        now = time.time()
        if fingerprint in self._match_cooldown:
            if (now - self._match_cooldown[fingerprint]) < self._cooldown_seconds:
                return None  # Cooldown active
        
        self._match_cooldown[fingerprint] = now
        
        # Confidence level
        if similarity >= 0.8:
            confidence = "HIGH"
        elif similarity >= 0.6:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        result = CrossCameraMatch(
            query_embedding=PersonEmbedding(
                embedding=embedding,
                camera_id=camera_id,
                track_id=track_id,
                timestamp=now,
                bbox=bbox,
                crop=person_crop,
            ),
            match_embedding=match_entry,
            similarity=similarity,
            time_gap=now - match_entry.timestamp,
            confidence=confidence,
        )
        
        # Also add new observation to gallery
        pe = PersonEmbedding(
            embedding=embedding,
            camera_id=camera_id,
            track_id=track_id,
            timestamp=now,
            bbox=bbox,
            crop=person_crop,
        )
        self._gallery.add(pe)
        
        logger.info(
            f"ReID: Cross-camera match! "
            f"{camera_id}:T{track_id} <-> {match_entry.camera_id}:T{match_entry.track_id} "
            f"(sim={similarity:.3f}, gap={result.time_gap:.0f}s, conf={confidence})"
        )
        
        return result
    
    def get_gallery_size(self) -> int:
        """Get current gallery size."""
        return self._gallery.get_stats()["gallery_size"]
    
    def get_stats(self) -> Dict:
        """Get full statistics."""
        return {
            **self._gallery.get_stats(),
            "model": self._model_name if not self._fallback_mode else "fallback_color_histogram",
            "device": self._device,
            "fallback_mode": self._fallback_mode,
            "cooldown_seconds": self._cooldown_seconds,
        }


# Module-level singleton
_reid_engine: Optional[ReIDEngine] = None


def get_reid_engine(**kwargs) -> ReIDEngine:
    """Get or create the singleton ReID engine."""
    global _reid_engine
    if _reid_engine is None:
        _reid_engine = ReIDEngine(**kwargs)
    return _reid_engine
