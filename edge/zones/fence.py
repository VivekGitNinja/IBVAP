"""
Virtual Fence / Zone Engine.

Supports:
- Polygon zones (restricted, sensitive, patrol, exclusion, monitoring)
- Entry / exit detection
- Crossing direction
- Dwell time tracking
- Zone severity
- Configurable thresholds
"""

from __future__ import annotations
from datetime import datetime
from typing import Any

from backend.app.services.geometry import point_in_polygon, polygon_centroid


class ZoneFence:
    """Manages virtual fence zones for a camera."""

    def __init__(self, zones: list[dict[str, Any]] | None = None):
        self.zones: list[dict[str, Any]] = zones or []
        self._zone_states: dict[str, dict] = {}  # track_id -> {zone_id: state}

    @property
    def is_available(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return True

    def set_zones(self, zones: list[dict[str, Any]]) -> None:
        """Update zone definitions."""
        self.zones = zones

    def check_position(
        self,
        track_id: str,
        position: tuple[int, int],
        frame_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Check a tracked object's position against all zones.

        Returns list of zone events (entries, exits, crossings).
        """
        now = frame_time or datetime.utcnow()
        events = []

        if track_id not in self._zone_states:
            self._zone_states[track_id] = {}

        prev_state = self._zone_states[track_id].copy()

        for zone in self.zones:
            zone_id = zone.get("id", 0)
            polygon = zone.get("polygon", [])
            if len(polygon) < 3:
                continue

            is_inside = point_in_polygon(position, polygon)
            was_inside = prev_state.get(zone_id, False)

            if is_inside and not was_inside:
                # Entry / crossing
                events.append({
                    "event_type": "zone_entry",
                    "zone_id": zone_id,
                    "zone_name": zone.get("name", ""),
                    "zone_type": zone.get("zone_type", "MONITORING"),
                    "position": list(position),
                    "severity": zone.get("severity", 0.5),
                    "timestamp": now.isoformat(),
                })
                # If this is a restricted zone, also emit a crossing event
                if zone.get("zone_type") in ("RESTRICTED", "SENSITIVE"):
                    events.append({
                        "event_type": "zone_crossing",
                        "zone_id": zone_id,
                        "zone_name": zone.get("name", ""),
                        "zone_type": zone.get("zone_type", ""),
                        "position": list(position),
                        "severity": zone.get("severity", 0.5),
                        "timestamp": now.isoformat(),
                    })

            elif not is_inside and was_inside:
                # Exit
                events.append({
                    "event_type": "zone_exit",
                    "zone_id": zone_id,
                    "zone_name": zone.get("name", ""),
                    "zone_type": zone.get("zone_type", "MONITORING"),
                    "position": list(position),
                    "timestamp": now.isoformat(),
                })

            self._zone_states[track_id][zone_id] = is_inside

        return events

    def get_zones_for_position(
        self, position: tuple[int, int]
    ) -> list[dict[str, Any]]:
        """Return all zones containing the given position."""
        containing = []
        for zone in self.zones:
            polygon = zone.get("polygon", [])
            if len(polygon) >= 3 and point_in_polygon(position, polygon):
                containing.append(zone)
        return containing

    def is_in_restricted_zone(self, position: tuple[int, int]) -> bool:
        """Check if a position is inside any restricted zone."""
        for zone in self.zones:
            if zone.get("zone_type") in ("RESTRICTED", "SENSITIVE"):
                polygon = zone.get("polygon", [])
                if len(polygon) >= 3 and point_in_polygon(position, polygon):
                    return True
        return False

    def cleanup_track(self, track_id: str) -> None:
        """Remove state for a completed track."""
        self._zone_states.pop(track_id, None)
