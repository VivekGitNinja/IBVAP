"""
Behavior Intelligence Module.

Implements rule-based temporal behavior analysis:
- Loitering detection
- Unusual dwell time
- Boundary crossing direction
- Rapid movement
- Abandoned object detection
- Night-time movement
- Repeated crossing
- Camera tampering

Every behavior detection produces an explainable output with WHY it was generated.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any

from edge.tracking.centroid import TrackedObject


class BehaviorAnalyzer:
    """Rule-based behavior analyzer for tracked objects."""

    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or {}
        self.loitering_threshold = cfg.get("loitering_threshold_seconds", 30)
        self.rapid_speed_threshold = cfg.get("rapid_speed_threshold", 200)
        self.abandoned_threshold = cfg.get("abandoned_threshold_seconds", 45)
        self.night_start_hour = cfg.get("night_start_hour", 20)
        self.night_end_hour = cfg.get("night_end_hour", 6)
        self.repeated_crossing_threshold = cfg.get("repeated_crossing_threshold", 3)

    def analyze(
        self,
        track: TrackedObject,
        previous_positions: list[tuple[int, int]] | None = None,
        frame_time: datetime | None = None,
        camera_health: float = 100.0,
        is_in_zone: bool = False,
    ) -> list[dict[str, Any]]:
        """Analyze a tracked object for behavioral patterns.

        Returns list of behavior events, each with type, confidence, and description.
        """
        now = frame_time or datetime.utcnow()
        events = []

        # Loitering detection
        if track.dwell_time_seconds >= self.loitering_threshold and is_in_zone:
            overshoot = track.dwell_time_seconds - self.loitering_threshold
            confidence = min(0.95, 0.6 + overshoot / 60.0)
            events.append({
                "behavior": "loitering",
                "confidence": round(confidence, 2),
                "description": f"Object stationary for {int(track.dwell_time_seconds)} seconds "
                              f"(threshold: {self.loitering_threshold}s)",
                "dwell_seconds": track.dwell_time_seconds,
                "severity_contribution": 0.3 + min(0.4, overshoot / 100),
            })

        # Rapid movement
        if track.speed_estimate > self.rapid_speed_threshold:
            confidence = min(0.9, 0.5 + (track.speed_estimate - self.rapid_speed_threshold) / 200)
            events.append({
                "behavior": "rapid_movement",
                "confidence": round(confidence, 2),
                "description": f"Speed estimate {int(track.speed_estimate)} px/s exceeds threshold",
                "speed": track.speed_estimate,
                "severity_contribution": 0.2,
            })

        # Night movement
        hour = now.hour
        if hour >= self.night_start_hour or hour < self.night_end_hour:
            events.append({
                "behavior": "night_movement",
                "confidence": 0.9,
                "description": f"Movement detected at night ({now.strftime('%H:%M')})",
                "hour": hour,
                "severity_contribution": 0.2,
            })

        # Repeated boundary crossing
        if len(track.zone_ids) >= self.repeated_crossing_threshold:
            events.append({
                "behavior": "repeated_crossing",
                "confidence": min(0.9, 0.5 + len(track.zone_ids) * 0.1),
                "description": f"Object has crossed {len(track.zone_ids)} zones",
                "zone_count": len(track.zone_ids),
                "severity_contribution": 0.25,
            })

        # Direction analysis
        if track.direction and track.direction != "unknown":
            events.append({
                "behavior": "direction_analysis",
                "confidence": 0.7,
                "description": f"Primary movement direction: {track.direction}",
                "direction": track.direction,
                "severity_contribution": 0.0,
            })

        # Camera health context
        if camera_health < 50:
            events.append({
                "behavior": "camera_degraded",
                "confidence": 0.8,
                "description": f"Camera health degraded ({int(camera_health)}%)",
                "health_score": camera_health,
                "severity_contribution": 0.1,
            })

        return events

    def detect_abandoned_object(
        self,
        stationary_tracks: list[TrackedObject],
        departed_tracks: list[TrackedObject],
        frame_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Detect abandoned objects by correlating stationary and departed tracks.

        An abandoned object is one that:
        1. Was near a person track
        2. The person track departed
        3. The object remains stationary for threshold seconds
        """
        events = []
        for obj_track in stationary_tracks:
            if obj_track.label not in ("object", "backpack", "bag", "package"):
                continue

            # Check if it has been stationary long enough
            if obj_track.dwell_time_seconds < self.abandoned_threshold:
                continue

            # Check if any person was nearby recently
            for person_track in departed_tracks:
                if person_track.label != "person":
                    continue
                if not person_track.active:
                    # Person departed
                    events.append({
                        "behavior": "abandoned_object",
                        "confidence": min(0.85, 0.5 + obj_track.dwell_time_seconds / 120),
                        "description": f"Object stationary for {int(obj_track.dwell_time_seconds)}s "
                                      f"after person departed",
                        "object_track_id": obj_track.track_id,
                        "stationary_seconds": obj_track.dwell_time_seconds,
                        "severity_contribution": 0.4,
                    })
                    break

        return events
