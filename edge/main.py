"""
IBVAP Edge Pipeline — Complete AI Perception System
===================================================

The edge pipeline runs near the CCTV source and performs:
1. Video Ingestion (RTSP, ONVIF, USB, file)
2. Frame Sampling (adaptive based on motion/scene)
3. ROI Processing (crop to regions of interest)
4. AI Perception:
   - Object Detection (YOLO26n — world's fastest, 40.9 mAP)
   - Multi-Object Tracking (ByteTrack — Kalman filter + IoU)
   - Face Detection (OpenCV DNN/Haar — privacy-preserving)
   - ANPR (Haar cascade + OCR pipeline)
5. Zone Engine (polygon zones, virtual fences)
6. Behavior Intelligence (loitering, crossing, rapid movement)
7. Context Engine (combines all signals into enriched events)

Architecture: Rule + AI Hybrid Intelligence
- AI Perception: "What is present?"
- Rules/Context: "What is happening?"
- Zone Engine: "Where is it?"
- Behavior: "How is it moving?"
- Scoring: "How serious is it?"

Honesty: Detection methods are truthfully labeled.
"""

import os
import sys
import time
import json
import logging
import threading
from typing import List, Dict, Optional, Callable
from collections import defaultdict

import cv2
import numpy as np

from edge.detection.base import Detector, Detection
from edge.detection.factory import create_detector
from edge.tracking.bytetrack import ByteTracker
from edge.zones.fence import ZoneFence
from edge.context.engine import ContextEngine
from edge.health.checks import CameraHealthChecker

logger = logging.getLogger(__name__)


class EdgePipeline:
    """Complete edge AI perception pipeline.
    
    Processes video frames through the full perception stack:
    Detection → Tracking → Zones → Behavior → Context → Events
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the edge pipeline.
        
        Args:
            config: Pipeline configuration dict
        """
        self.config = config or {}
        self._running = False
        self._frame_count = 0
        self._start_time = time.time()

        # Detector — auto-selects YOLO26n > YOLO11n > Motion
        detector_name = self.config.get("detector", None)
        confidence = self.config.get("confidence", 0.25)
        self.detector: Detector = create_detector(
            preferred=detector_name,
            confidence_threshold=confidence,
            border_only=self.config.get("border_only", False),
        )

        # Tracker — ByteTrack with Kalman filter
        self.tracker = ByteTracker(
            high_thresh=self.config.get("high_confidence", 0.6),
            low_thresh=self.config.get("low_confidence", 0.1),
            track_buffer=self.config.get("track_buffer", 30),
        )

        # Zone engine
        self.zone_engine = ZoneFence()

        # Context engine (behavior analysis + event generation)
        self.context_engine = None  # Initialized lazily per-camera

        # Health checker
        self.health_checker = CameraHealthChecker()

        # ANPR (optional)
        self._anpr = None
        if self.config.get("enable_anpr", False):
            try:
                from edge.detection.anpr import ANPRPipeline
                self._anpr = ANPRPipeline()
            except Exception as e:
                logger.warning(f"ANPR not available: {e}")

        # Face detector (optional)
        self._face_detector = None
        if self.config.get("enable_faces", False):
            try:
                from edge.detection.face_detector import FaceDetector
                self._face_detector = FaceDetector(
                    confidence_threshold=self.config.get("face_confidence", 0.5)
                )
            except Exception as e:
                logger.warning(f"Face detector not available: {e}")

        # Frame sampling
        self._sample_interval = self.config.get("sample_interval", 1)
        self._motion_threshold = self.config.get("motion_threshold", 500)
        self._prev_gray = None

        # Event callback
        self._event_callback: Optional[Callable] = None

        # Stats
        self._stats = {
            "frames_processed": 0,
            "frames_skipped": 0,
            "detections_total": 0,
            "tracks_active": 0,
            "events_generated": 0,
            "inference_times": [],
        }

        logger.info(
            f"Edge pipeline initialized: detector={self.detector.name}, "
            f"tracker=ByteTrack, zones=ZoneFence"
        )

    def set_event_callback(self, callback: Callable):
        """Set callback for generated events."""
        self._event_callback = callback

    def process_frame(self, frame: np.ndarray, frame_id: Optional[int] = None,
                      camera_id: str = "CAM-01") -> Dict:
        """Process a single frame through the full pipeline.
        
        Args:
            frame: BGR image (H, W, 3)
            frame_id: frame sequence number
            camera_id: camera identifier
            
        Returns:
            Complete processing result with detections, tracks, events
        """
        if frame_id is None:
            frame_id = self._frame_count
        self._frame_count += 1

        result = {
            "frame_id": frame_id,
            "camera_id": camera_id,
            "timestamp": time.time(),
            "detections": [],
            "tracks": [],
            "events": [],
            "face_detections": [],
            "anpr_results": [],
            "health": {},
            "inference_ms": 0,
        }

        try:
            # Adaptive frame sampling
            if not self._should_process(frame):
                result["skipped"] = True
                self._stats["frames_skipped"] += 1
                return result

            # 1. Object Detection
            start = time.time()
            detections = self.detector.detect(frame, frame_id)
            inference_ms = (time.time() - start) * 1000
            result["inference_ms"] = inference_ms
            self._stats["inference_times"].append(inference_ms)
            if len(self._stats["inference_times"]) > 100:
                self._stats["inference_times"] = self._stats["inference_times"][-100:]

            # Convert detections to dict format
            det_dicts = []
            for d in detections:
                det_dicts.append({
                    "bbox": d.bbox,
                    "class_id": d.class_id,
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                })
            result["detections"] = det_dicts
            self._stats["detections_total"] += len(det_dicts)

            # 2. Multi-Object Tracking (ByteTrack)
            tracks = self.tracker.update(det_dicts)
            result["tracks"] = tracks
            self._stats["tracks_active"] = len(tracks)

            # 3. Face Detection (if enabled)
            if self._face_detector and self._face_detector.is_available:
                faces = self._face_detector.detect(frame, frame_id)
                result["face_detections"] = [f.to_dict() for f in faces]

            # 4. ANPR (if enabled)
            if self._anpr and self._anpr.is_available:
                vehicle_dets = [d for d in det_dicts
                               if d["class_name"] in ("car", "truck", "bus", "motorcycle")]
                if vehicle_dets:
                    plate_results = self._anpr.process_frame(frame, vehicle_dets)
                    result["anpr_results"] = [p.to_dict() for p in plate_results]

            # 5. Zone checking for tracked objects
            zone_events = []
            for track in tracks:
                bbox = track["bbox"]
                center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
                crossings = self.zone_engine.check_crossing(
                    track["track_id"], center, bbox
                )
                zone_events.extend(crossings)

            # 6. Context Engine (behavior analysis)
            context_events = self.context_engine.process(
                tracks=tracks,
                detections=det_dicts,
                zone_events=zone_events,
                frame_id=frame_id,
                camera_id=camera_id,
                timestamp=time.time(),
            )

            all_events = zone_events + context_events
            result["events"] = all_events
            self._stats["events_generated"] += len(all_events)

            # 7. Fire event callback
            for event in all_events:
                if self._event_callback:
                    try:
                        self._event_callback(event)
                    except Exception as e:
                        logger.error(f"Event callback error: {e}")

            # 8. Health check
            result["health"] = self.health_checker.check_frame(
                frame, inference_ms
            )

        except Exception as e:
            logger.error(f"Pipeline error on frame {frame_id}: {e}")
            result["error"] = str(e)

        return result

    def _should_process(self, frame: np.ndarray) -> bool:
        """Adaptive frame sampling — process more when motion detected."""
        # Always process at sample interval
        if self._frame_count % self._sample_interval == 0:
            return True

        # Check for motion to trigger extra processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 240))

        if self._prev_gray is not None:
            diff = cv2.absdiff(self._prev_gray, gray)
            motion_pixels = cv2.countNonZero(
                cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            )

            if motion_pixels > self._motion_threshold:
                # Motion detected — process more frequently
                self._prev_gray = gray
                return True

        self._prev_gray = gray
        return False

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        uptime = time.time() - self._start_time
        avg_inference = 0
        if self._stats["inference_times"]:
            avg_inference = sum(self._stats["inference_times"]) / len(
                self._stats["inference_times"]
            )

        return {
            "uptime_seconds": round(uptime, 1),
            "frames_processed": self._stats["frames_processed"],
            "frames_skipped": self._stats["frames_skipped"],
            "detections_total": self._stats["detections_total"],
            "tracks_active": self._stats["tracks_active"],
            "events_generated": self._stats["events_generated"],
            "avg_inference_ms": round(avg_inference, 1),
            "detector": self.detector.name,
            "tracker": "ByteTrack",
        }

    def reset(self):
        """Reset pipeline state."""
        self._frame_count = 0
        self._start_time = time.time()
        self._prev_gray = None
        self.tracker.reset()
        self.zone_engine.reset()
        self.context_engine.reset()
        self._stats = {
            "frames_processed": 0,
            "frames_skipped": 0,
            "detections_total": 0,
            "tracks_active": 0,
            "events_generated": 0,
            "inference_times": [],
        }
