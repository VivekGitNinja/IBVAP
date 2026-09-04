"""
Centroid / IoU-based Object Tracker.

Lightweight tracker that assigns persistent IDs to detected objects
across frames. Supports:
- Track ID
- Bounding box
- Class/label
- Confidence
- First seen / last seen
- Trajectory (position history)
- Dwell time
- Direction estimation
- Speed estimation
- Zone membership
- Survives temporary detection loss
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import math

from edge.detection.base import Detection
from backend.app.services.geometry import bbox_iou, point_distance, direction_label


# Maximum frames a track can survive without a matching detection
MAX_DISAPPEARED = 10
# IoU threshold for matching a detection to an existing track
IOU_THRESHOLD = 0.3


@dataclass
class TrackedObject:
    """A single tracked object across frames."""
    track_id: str
    label: str
    confidence_avg: float = 0.0
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
    trajectory: list[list] = field(default_factory=list)
    dwell_time_seconds: float = 0.0
    total_distance: float = 0.0
    speed_estimate: float = 0.0
    direction: str = "unknown"
    zone_ids: list[int] = field(default_factory=list)
    current_zone_id: Optional[int] = None
    frame_count: int = 0
    first_frame: int = 0
    last_frame: int = 0
    max_speed: float = 0.0
    last_bbox: dict = field(default_factory=dict)
    disappeared: int = 0

    @property
    def center(self) -> tuple[int, int]:
        bbox = self.last_bbox
        if not bbox:
            return (0, 0)
        return ((bbox["x1"] + bbox["x2"]) // 2, (bbox["y1"] + bbox["y2"]) // 2)

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "confidence_avg": round(self.confidence_avg, 3),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "active": self.active,
            "trajectory": self.trajectory[-50:],  # Keep last 50 points
            "dwell_time_seconds": round(self.dwell_time_seconds, 1),
            "total_distance": round(self.total_distance, 1),
            "speed_estimate": round(self.speed_estimate, 1),
            "max_speed": round(self.max_speed, 1),
            "first_frame": self.first_frame,
            "last_frame": self.last_frame,
            "direction": self.direction,
            "zone_ids": self.zone_ids,
            "current_zone_id": self.current_zone_id,
            "frame_count": self.frame_count,
            "last_bbox": self.last_bbox,
        }


class CentroidTracker:
    """IoU-based multi-object tracker.

    Matches detections to existing tracks using IoU. Unmatched detections
    create new tracks. Tracks that lose detections persist for MAX_DISAPPEARED
    frames before being marked inactive.
    """

    def __init__(self, iou_threshold: float = IOU_THRESHOLD,
                 max_disappeared: int = MAX_DISAPPEARED):
        self.iou_threshold = iou_threshold
        self.max_disappeared = max_disappeared
        self.tracks: dict[str, TrackedObject] = {}
        self._next_id = 1
        self._last_frame_time: datetime | None = None

    def update(self, detections: list[Detection], frame_time: datetime | None = None) -> list[TrackedObject]:
        """Update tracker with new detections.

        Returns list of all currently active tracked objects.
        """
        now = frame_time or datetime.utcnow()
        dt_seconds = 1.0
        if self._last_frame_time:
            dt_seconds = max(0.1, (now - self._last_frame_time).total_seconds())
        self._last_frame_time = now

        if not detections:
            # No detections — increment disappeared count for all tracks
            for track in self.tracks.values():
                track.disappeared += 1
                if track.disappeared > self.max_disappeared:
                    track.active = False
            return [t for t in self.tracks.values() if t.active]

        # Build list of bounding boxes from detections
        det_bboxes = [d.bbox for d in detections]

        if not self.tracks:
            # No existing tracks — register all detections
            for det in detections:
                self._register_track(det, now)
        else:
            # Match existing tracks to new detections using IoU
            self._match_and_update(detections, det_bboxes, now, dt_seconds)

        return [t for t in self.tracks.values() if t.active]

    def _register_track(self, det: Detection, now: datetime) -> None:
        """Create a new track from a detection."""
        tid = f"T-{self._next_id:04d}"
        self._next_id += 1
        det.track_id = tid

        cx, cy = det.center
        fid = getattr(det, "frame_id", 0)
        label_val = getattr(det, "class_name", "") or getattr(det, "label", "unknown")
        if label_val == "unknown" and getattr(det, "label", ""):
            label_val = det.label

        track = TrackedObject(
            track_id=tid,
            label=label_val,
            confidence_avg=det.confidence,
            first_seen=now,
            last_seen=now,
            trajectory=[[cx, cy, now.isoformat()]],
            last_bbox={"x1": det.bbox[0], "y1": det.bbox[1],
                       "x2": det.bbox[2], "y2": det.bbox[3]},
            frame_count=1,
            first_frame=fid,
            last_frame=fid,
        )
        self.tracks[tid] = track

    def _match_and_update(self, detections: list[Detection],
                           det_bboxes: list[tuple], now: datetime,
                           dt_seconds: float) -> None:
        """Match detections to existing tracks and update them."""
        active_tracks = {tid: t for tid, t in self.tracks.items() if t.active}

        if not active_tracks:
            for det in detections:
                self._register_track(det, now)
            return

        # Compute IoU matrix
        track_ids = list(active_tracks.keys())
        track_bboxes = [active_tracks[tid].last_bbox for tid in track_ids]
        track_bboxes_tuples = [
            (b.get("x1", 0), b.get("y1", 0), b.get("x2", 0), b.get("y2", 0))
            for b in track_bboxes
        ]

        # Greedy matching by IoU
        matched_tracks = set()
        matched_dets = set()

        # Build IoU pairs
        iou_pairs = []
        for ti, tb in enumerate(track_bboxes_tuples):
            for di, db in enumerate(det_bboxes):
                iou = bbox_iou(tb, db)
                if iou >= self.iou_threshold:
                    iou_pairs.append((iou, ti, di))

        # Sort by IoU descending (best matches first)
        iou_pairs.sort(key=lambda x: x[0], reverse=True)

        for iou_val, ti, di in iou_pairs:
            if ti in matched_tracks or di in matched_dets:
                continue
            tid = track_ids[ti]
            det = detections[di]
            det.track_id = tid
            track = active_tracks[tid]

            # Update track
            cx, cy = det.center
            prev_center = (track.trajectory[-1][0] if track.trajectory else cx,
                          track.trajectory[-1][1] if track.trajectory else cy)

            dist = point_distance(prev_center, (cx, cy))
            track.total_distance += dist
            if dt_seconds > 0:
                track.speed_estimate = dist / dt_seconds
                track.max_speed = max(track.max_speed, track.speed_estimate)

            dx = cx - prev_center[0]
            dy = cy - prev_center[1]
            if abs(dx) > 5 or abs(dy) > 5:
                track.direction = direction_label(dx, dy)

            track.trajectory.append([cx, cy, now.isoformat()])
            track.last_bbox = {"x1": det.bbox[0], "y1": det.bbox[1],
                              "x2": det.bbox[2], "y2": det.bbox[3]}
            track.last_seen = now
            track.frame_count += 1
            fid = getattr(det, "frame_id", 0)
            if fid > 0:
                track.last_frame = fid
            else:
                track.last_frame += 1

            track.disappeared = 0
            track.active = True

            # Update rolling average confidence
            n = track.frame_count
            track.confidence_avg = (
                track.confidence_avg * (n - 1) + det.confidence
            ) / n

            # Update dwell time
            track.dwell_time_seconds += dt_seconds

            matched_tracks.add(ti)
            matched_dets.add(di)

        # Unmatched tracks — increment disappeared
        for ti, tid in enumerate(track_ids):
            if ti not in matched_tracks:
                track = active_tracks[tid]
                track.disappeared += 1
                if track.disappeared > self.max_disappeared:
                    track.active = False

        # Unmatched detections — create new tracks
        for di, det in enumerate(detections):
            if di not in matched_dets:
                self._register_track(det, now)

    def get_track_summaries(self) -> dict[str, dict]:
        """Return high-level summary of all tracks observed."""
        return {
            tid: {
                "track_id": t.track_id,
                "class": t.label,
                "first_frame": t.first_frame,
                "last_frame": t.last_frame,
                "max_speed": round(t.max_speed, 2),
                "total_distance": round(t.total_distance, 2),
                "frame_count": t.frame_count,
                "dwell_time_seconds": round(t.dwell_time_seconds, 2),
                "direction": t.direction,
            }
            for tid, t in self.tracks.items()
        }

    def get_active_tracks(self) -> list[TrackedObject]:
        """Return currently active tracks."""
        return [t for t in self.tracks.values() if t.active]

    def get_track_by_id(self, track_id: str) -> TrackedObject | None:
        """Look up a track by its ID."""
        return self.tracks.get(track_id)

    def cleanup(self) -> int:
        """Remove inactive tracks. Returns count removed."""
        inactive = [tid for tid, t in self.tracks.items() if not t.active]
        for tid in inactive:
            del self.tracks[tid]
        return len(inactive)

    @property
    def active_count(self) -> int:
        return sum(1 for t in self.tracks.values() if t.active)

    @property
    def total_count(self) -> int:
        return len(self.tracks)

