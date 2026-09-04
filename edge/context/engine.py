"""
Context Engine — combines perception, tracking, zones, and behavior analysis.

This is the "What is happening?" layer that sits between raw detection
and incident generation. It maintains state across frames and produces
enriched events for the scoring engine.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any

from edge.tracking.centroid import CentroidTracker, TrackedObject
from edge.context import BehaviorAnalyzer
from edge.zones.fence import ZoneFence


class ContextEngine:
    """Manages the full per-camera analysis context."""

    def __init__(self, camera_id: int, zones: list[dict] | None = None,
                 behavior_config: dict | None = None):
        self.camera_id = camera_id
        self.tracker = CentroidTracker()
        self.behavior = BehaviorAnalyzer(behavior_config)
        self.fence = ZoneFence(zones or [])
        self.frame_count = 0
        self._events_log: list[dict] = []

    def process_frame(
        self,
        detections: list[Any],
        frame_time: datetime | None = None,
        camera_health: float = 100.0,
    ) -> dict[str, Any]:
        """Process a single frame through the full context pipeline.

        Returns enriched events and current state.
        """
        now = frame_time or datetime.utcnow()
        self.frame_count += 1

        # Track objects
        tracks = self.tracker.update(detections, now)

        # Analyze each track
        all_events = []
        zone_events_all = []
        behavior_events_all = []

        for track in tracks:
            center = (
                (track.last_bbox.get("x1", 0) + track.last_bbox.get("x2", 0)) // 2,
                (track.last_bbox.get("y1", 0) + track.last_bbox.get("y2", 0)) // 2,
            )

            # Zone checks
            in_zone = self.fence.is_in_restricted_zone(center)
            ze = self.fence.check_position(track.track_id, center, now)
            zone_events_all.extend(ze)

            # Update track zone membership
            for zev in ze:
                zid = zev.get("zone_id")
                if zid and zid not in track.zone_ids:
                    track.zone_ids.append(zid)
                if zev.get("event_type") == "zone_entry":
                    track.current_zone_id = zid

            # Behavior analysis
            be = self.behavior.analyze(
                track, frame_time=now, camera_health=camera_health,
                is_in_zone=in_zone,
            )
            behavior_events_all.extend(be)

            # Create enriched events
            for zev in ze:
                evt = {
                    "camera_id": self.camera_id,
                    "event_type": zev["event_type"],
                    "object_type": track.label,
                    "track_id": track.track_id,
                    "confidence": track.confidence_avg,
                    "zone_id": zev.get("zone_id"),
                    "severity": zev.get("severity", 0),
                    "payload": {
                        "track": track.to_dict(),
                        "zone_name": zev.get("zone_name", ""),
                        "position": zev.get("position", []),
                        "zone_type": zev.get("zone_type", ""),
                    },
                    "occurred_at": now.isoformat(),
                }
                all_events.append(evt)

            for bev in behavior_events_all:
                if bev.get("confidence", 0) > 0.5:
                    evt = {
                        "camera_id": self.camera_id,
                        "event_type": bev["behavior"],
                        "object_type": track.label,
                        "track_id": track.track_id,
                        "confidence": bev["confidence"],
                        "severity": bev.get("severity_contribution", 0),
                        "payload": {
                            "track": track.to_dict(),
                            "description": bev.get("description", ""),
                            **{k: v for k, v in bev.items()
                               if k not in ("behavior", "confidence", "description",
                                           "severity_contribution")},
                        },
                        "occurred_at": now.isoformat(),
                    }
                    all_events.append(evt)

        self._events_log.extend(all_events)

        return {
            "frame": self.frame_count,
            "tracks": [t.to_dict() for t in tracks],
            "events": all_events,
            "active_tracks": len(tracks),
            "zone_events": zone_events_all,
            "behavior_events": behavior_events_all,
        }

    def get_state(self) -> dict[str, Any]:
        """Get current engine state."""
        return {
            "camera_id": self.camera_id,
            "frame_count": self.frame_count,
            "active_tracks": self.tracker.active_count,
            "total_tracks": self.tracker.total_count,
            "events_count": len(self._events_log),
        }
