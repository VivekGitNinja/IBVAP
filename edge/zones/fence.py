"""
Virtual Fence / Zone Engine.

Supports:
- Polygon zones (restricted, sensitive, patrol, exclusion, monitoring)
- Line tripwire zones with direction control ('either', 'a_to_b', 'b_to_a')
- Entry / exit detection
- Cooldown suppression of duplicate incidents
- Armed schedule and night-only filtering
- Behavior rules: Loitering, Crowd Gathering, Rapid Movement
- Zone visualization and overlay drawing
"""

from __future__ import annotations
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from backend.app.services.geometry import (
    point_in_polygon,
    polygon_centroid,
    check_line_crossing,
    point_distance,
)


class ZoneFence:
    """Manages virtual fence zones and tactical behavioral rules."""

    def __init__(
        self,
        zones: list[dict[str, Any]] | None = None,
        default_cooldown_seconds: float = 10.0,
        loitering_seconds: float = 60.0,
        crowd_min_count: int = 5,
        crowd_window_seconds: float = 30.0,
        rapid_speed_threshold: float = 200.0,
    ):
        self.zones: list[dict[str, Any]] = zones or []
        self.default_cooldown_seconds = default_cooldown_seconds
        self.loitering_seconds = loitering_seconds
        self.crowd_min_count = crowd_min_count
        self.crowd_window_seconds = crowd_window_seconds
        self.rapid_speed_threshold = rapid_speed_threshold

        self._zone_states: dict[str, dict[int, bool]] = {}  # track_id -> {zone_id: was_inside}
        self._track_prev_positions: dict[str, tuple[float, float]] = {}
        self._cooldowns: dict[tuple[str, int, str], float] = {}  # (track_id, zone_id, event_type) -> timestamp
        self._zone_entry_timestamps: dict[tuple[str, int], float] = {}  # (track_id, zone_id) -> entry timestamp
        self._zone_occupants: dict[int, dict[str, float]] = {}  # zone_id -> {track_id: timestamp}
        self._behavior_cooldowns: dict[tuple[str, str], float] = {}  # (rule_name, key) -> timestamp

    @property
    def is_available(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return True

    def set_zones(self, zones: list[dict[str, Any]]) -> None:
        """Update zone definitions."""
        self.zones = zones

    def _is_zone_armed(self, zone: dict[str, Any], frame_time: datetime) -> bool:
        """Check if zone is currently armed according to schedule."""
        schedule = zone.get("armed_schedule")
        if not schedule or not isinstance(schedule, dict):
            return True

        # Weekdays: mon, tue, wed, thu, fri, sat, sun
        weekday_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        current_day = weekday_map[frame_time.weekday()]

        windows = schedule.get(current_day)
        if windows is None:
            # Fallback check for integer day or 'all'
            windows = schedule.get("all") or schedule.get(str(frame_time.weekday()))
        if not windows:
            return False

        current_time_str = frame_time.strftime("%H:%M")
        for window in windows:
            if isinstance(window, (list, tuple)) and len(window) >= 2:
                start, end = str(window[0]), str(window[1])
                if start <= current_time_str <= end:
                    return True
        return False

    def _resolve_geometry(
        self,
        zone: dict[str, Any],
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
    ) -> tuple[str, list[list[float]]]:
        """Normalize or scale zone points based on frame size."""
        geom = zone.get("geometry")
        if isinstance(geom, dict) and "points" in geom:
            g_type = geom.get("type", "polygon")
            pts = geom.get("points", [])
        else:
            g_type = "polygon"
            pts = zone.get("polygon", [])

        if not pts:
            return g_type, []

        # Check if coordinates are normalized [0..1]
        is_normalized = all(
            0.0 <= pt[0] <= 1.05 and 0.0 <= pt[1] <= 1.05
            for pt in pts if len(pt) >= 2
        )

        if is_normalized and frame_width and frame_height:
            scaled_pts = [
                [pt[0] * frame_width, pt[1] * frame_height]
                for pt in pts if len(pt) >= 2
            ]
            return g_type, scaled_pts

        return g_type, pts

    def check_position(
        self,
        track_id: str,
        position: tuple[float, float],
        frame_time: datetime | None = None,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        is_night: bool = False,
        confidence: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Check a tracked object's position against all zones.

        Returns list of zone events (entries, exits, crossings, intrusions).
        """
        now = frame_time or datetime.utcnow()
        now_ts = now.timestamp()
        events: list[dict[str, Any]] = []

        if track_id not in self._zone_states:
            self._zone_states[track_id] = {}

        prev_pos = self._track_prev_positions.get(track_id, position)
        prev_state = self._zone_states[track_id].copy()

        for zone in self.zones:
            zone_id = zone.get("id", 0)
            name = zone.get("name", f"Zone-{zone_id}")
            zone_type = zone.get("zone_type", "RESTRICTED")
            severity = float(zone.get("severity", 0.5))
            min_conf = float(zone.get("min_confidence", 0.0))
            night_only = bool(zone.get("night_only", False))
            direction_rule = zone.get("direction", "either")

            # 1. Confidence check
            if confidence < min_conf:
                continue

            # 2. Night-only check
            if night_only and not is_night:
                continue

            # 3. Armed schedule check
            if not self._is_zone_armed(zone, now):
                continue

            g_type, points = self._resolve_geometry(zone, frame_width, frame_height)

            # ── LINE TRIPWIRE ZONE ───────────────────────────────────────
            if g_type == "line" and len(points) >= 2:
                line_a = (float(points[0][0]), float(points[0][1]))
                line_b = (float(points[1][0]), float(points[1][1]))

                crossed, dir_detected = check_line_crossing(
                    prev_pos, position, line_a, line_b, direction_rule=direction_rule
                )

                if crossed:
                    cooldown_key = (track_id, zone_id, "zone_intrusion")
                    last_time = self._cooldowns.get(cooldown_key)
                    if last_time is None or (now_ts - last_time) >= self.default_cooldown_seconds:
                        self._cooldowns[cooldown_key] = now_ts

                        events.append({
                            "event_type": "zone_intrusion",
                            "zone_id": zone_id,
                            "zone_name": name,
                            "zone_type": zone_type,
                            "position": list(position),
                            "severity": severity,
                            "direction": dir_detected,
                            "timestamp": now.isoformat(),
                            "rule": "line_tripwire",
                        })

                        if direction_rule != "either" and dir_detected != direction_rule:
                            events.append({
                                "event_type": "direction_violation",
                                "zone_id": zone_id,
                                "zone_name": name,
                                "zone_type": zone_type,
                                "position": list(position),
                                "severity": severity,
                                "direction": dir_detected,
                                "timestamp": now.isoformat(),
                            })

            # ── POLYGON PERIMETER ZONE ────────────────────────────────────
            elif len(points) >= 3:
                is_inside = point_in_polygon(position, points)
                was_inside = prev_state.get(zone_id, False)

                if is_inside and not was_inside:
                    # Transition outside -> inside: Entry / Intrusion
                    events.append({
                        "event_type": "zone_entry",
                        "zone_id": zone_id,
                        "zone_name": name,
                        "zone_type": zone_type,
                        "position": list(position),
                        "severity": severity,
                        "timestamp": now.isoformat(),
                    })

                    # Maintain legacy zone_crossing event for restricted/sensitive
                    if zone_type in ("RESTRICTED", "SENSITIVE"):
                        events.append({
                            "event_type": "zone_crossing",
                            "zone_id": zone_id,
                            "zone_name": name,
                            "zone_type": zone_type,
                            "position": list(position),
                            "severity": severity,
                            "timestamp": now.isoformat(),
                        })

                    # Cooldown-gated zone_intrusion incident
                    cooldown_key = (track_id, zone_id, "zone_intrusion")
                    last_time = self._cooldowns.get(cooldown_key)
                    if last_time is None or (now_ts - last_time) >= self.default_cooldown_seconds:
                        self._cooldowns[cooldown_key] = now_ts
                        events.append({
                            "event_type": "zone_intrusion",
                            "zone_id": zone_id,
                            "zone_name": name,
                            "zone_type": zone_type,
                            "position": list(position),
                            "severity": severity,
                            "timestamp": now.isoformat(),
                            "rule": "polygon_entry",
                        })

                    self._zone_entry_timestamps[(track_id, zone_id)] = now_ts
                    if zone_id not in self._zone_occupants:
                        self._zone_occupants[zone_id] = {}
                    self._zone_occupants[zone_id][track_id] = now_ts

                elif not is_inside and was_inside:
                    # Transition inside -> outside: Exit
                    events.append({
                        "event_type": "zone_exit",
                        "zone_id": zone_id,
                        "zone_name": name,
                        "zone_type": zone_type,
                        "position": list(position),
                        "timestamp": now.isoformat(),
                    })
                    self._zone_entry_timestamps.pop((track_id, zone_id), None)
                    if zone_id in self._zone_occupants:
                        self._zone_occupants[zone_id].pop(track_id, None)

                elif is_inside:
                    # Continues inside
                    if zone_id not in self._zone_occupants:
                        self._zone_occupants[zone_id] = {}
                    self._zone_occupants[zone_id][track_id] = now_ts

                self._zone_states[track_id][zone_id] = is_inside

        self._track_prev_positions[track_id] = position
        return events

    def check_behaviors(
        self,
        tracks: list[Any],
        frame_time: datetime | None = None,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Evaluate deterministic behavioral rules (loitering, crowd, rapid movement)."""
        now = frame_time or datetime.utcnow()
        now_ts = now.timestamp()
        behavior_events: list[dict[str, Any]] = []

        track_map = {t.track_id: t for t in tracks if getattr(t, "active", True)}

        for zone in self.zones:
            zone_id = zone.get("id", 0)
            name = zone.get("name", f"Zone-{zone_id}")
            g_type, points = self._resolve_geometry(zone, frame_width, frame_height)
            if g_type != "polygon" or len(points) < 3:
                continue

            dwell_thresh = float(zone.get("dwell_threshold_seconds") or self.loitering_seconds)
            occupants = self._zone_occupants.get(zone_id, {})

            # ── 1. LOITERING RULE ─────────────────────────────────────────
            for tid, entry_ts in list(occupants.items()):
                if tid not in track_map:
                    continue
                dwell_time = now_ts - entry_ts
                if dwell_time >= dwell_thresh:
                    cooldown_key = ("loitering", f"{tid}_{zone_id}")
                    last_btime = self._behavior_cooldowns.get(cooldown_key)
                    if last_btime is None or (now_ts - last_btime) >= self.default_cooldown_seconds:
                        self._behavior_cooldowns[cooldown_key] = now_ts
                        t_obj = track_map[tid]
                        behavior_events.append({
                            "event_type": "loitering",
                            "track_id": tid,
                            "zone_id": zone_id,
                            "zone_name": name,
                            "dwell_seconds": round(dwell_time, 1),
                            "threshold_seconds": dwell_thresh,
                            "position": list(t_obj.center),
                            "severity": 0.75,
                            "timestamp": now.isoformat(),
                        })

            # ── 2. CROWD GATHERING RULE ───────────────────────────────────
            # Count active occupants within crowd_window_seconds
            active_occupants = [
                tid for tid, last_seen_ts in occupants.items()
                if tid in track_map and (now_ts - last_seen_ts) <= self.crowd_window_seconds
            ]
            crowd_limit = int(zone.get("crowd_threshold") or self.crowd_min_count)
            if len(active_occupants) >= crowd_limit:
                cooldown_key = ("crowd_gathering", str(zone_id))
                last_btime = self._behavior_cooldowns.get(cooldown_key)
                if last_btime is None or (now_ts - last_btime) >= self.default_cooldown_seconds:
                    self._behavior_cooldowns[cooldown_key] = now_ts
                    behavior_events.append({
                        "event_type": "crowd_gathering",
                        "zone_id": zone_id,
                        "zone_name": name,
                        "track_ids": active_occupants,
                        "count": len(active_occupants),
                        "threshold": crowd_limit,
                        "severity": 0.85,
                        "timestamp": now.isoformat(),
                    })

        # ── 3. RAPID MOVEMENT RULE ────────────────────────────────────────
        for t in tracks:
            if not getattr(t, "active", True):
                continue
            speed = getattr(t, "speed_estimate", 0.0)
            bbox = getattr(t, "last_bbox", {})
            h = abs(bbox.get("y2", 0) - bbox.get("y1", 0)) if bbox else 0

            # Rapid condition: speed > threshold or > 3.5 body heights per sec
            is_rapid = speed >= self.rapid_speed_threshold or (h > 20 and (speed / h) >= 3.5)
            if is_rapid:
                cooldown_key = ("rapid_movement", t.track_id)
                last_btime = self._behavior_cooldowns.get(cooldown_key)
                if last_btime is None or (now_ts - last_btime) >= self.default_cooldown_seconds:
                    self._behavior_cooldowns[cooldown_key] = now_ts
                    behavior_events.append({
                        "event_type": "rapid_movement",
                        "track_id": t.track_id,
                        "speed": round(speed, 1),
                        "threshold": self.rapid_speed_threshold,
                        "position": list(t.center),
                        "severity": 0.70,
                        "timestamp": now.isoformat(),
                    })

        return behavior_events

    def get_zones_for_position(
        self, position: tuple[float, float], frame_width: Optional[int] = None, frame_height: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return all zones containing the given position."""
        containing = []
        for zone in self.zones:
            g_type, points = self._resolve_geometry(zone, frame_width, frame_height)
            if g_type == "polygon" and len(points) >= 3 and point_in_polygon(position, points):
                containing.append(zone)
        return containing

    def is_in_restricted_zone(
        self, position: tuple[float, float], frame_width: Optional[int] = None, frame_height: Optional[int] = None
    ) -> bool:
        """Check if a position is inside any restricted zone."""
        for zone in self.zones:
            if zone.get("zone_type") in ("RESTRICTED", "SENSITIVE"):
                g_type, points = self._resolve_geometry(zone, frame_width, frame_height)
                if g_type == "polygon" and len(points) >= 3 and point_in_polygon(position, points):
                    return True
        return False

    def cleanup_track(self, track_id: str) -> None:
        """Remove state for a completed track."""
        self._zone_states.pop(track_id, None)
        self._track_prev_positions.pop(track_id, None)
        for zid, occs in self._zone_occupants.items():
            occs.pop(track_id, None)
        keys_to_del = [k for k in self._cooldowns if k[0] == track_id]
        for k in keys_to_del:
            del self._cooldowns[k]
        keys_to_del_entry = [k for k in self._zone_entry_timestamps if k[0] == track_id]
        for k in keys_to_del_entry:
            del self._zone_entry_timestamps[k]

    def draw_zones_on_frame(
        self,
        frame: np.ndarray,
        triggered_zone_ids: Optional[Set[int]] = None,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
    ) -> np.ndarray:
        """Draw virtual fence lines and polygons on an annotated frame."""
        triggered = triggered_zone_ids or set()
        h, w = frame.shape[:2]
        fw = frame_width or w
        fh = frame_height or h

        for zone in self.zones:
            zid = zone.get("id", 0)
            name = zone.get("name", f"Z-{zid}")
            is_trig = zid in triggered
            color = (0, 0, 255) if is_trig else (0, 255, 128)  # BGR
            thickness = 3 if is_trig else 2

            g_type, points = self._resolve_geometry(zone, fw, fh)
            if not points:
                continue

            pts_arr = np.array([[int(p[0]), int(p[1])] for p in points], np.int32)

            if g_type == "line" and len(pts_arr) >= 2:
                cv2.line(frame, tuple(pts_arr[0]), tuple(pts_arr[1]), color, thickness)
                mid_x = int((pts_arr[0][0] + pts_arr[1][0]) / 2)
                mid_y = int((pts_arr[0][1] + pts_arr[1][1]) / 2)
                cv2.putText(frame, f"[FENCE] {name}", (mid_x, max(20, mid_y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            elif len(pts_arr) >= 3:
                cv2.polylines(frame, [pts_arr], True, color, thickness)
                cx, cy = polygon_centroid([[float(p[0]), float(p[1])] for p in points])
                cv2.putText(frame, f"[ZONE] {name}", (int(cx) - 30, int(cy)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return frame

