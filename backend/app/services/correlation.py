"""
Incident Correlation Engine.

Combines temporally and geographically related events from multiple cameras
into correlated incidents. Does NOT claim biometric identity across cameras —
uses anonymous track/session identifiers.
"""

from __future__ import annotations
import math
from datetime import datetime, timedelta
from typing import Any


# Maximum time gap (seconds) between events to consider them correlated
CORRELATION_TIME_WINDOW_SECONDS = 300  # 5 minutes

# Maximum distance (meters) between cameras for spatial correlation
CORRELATION_DISTANCE_METERS = 500.0


def should_correlate(
    existing_incident_time: datetime,
    event_time: datetime,
    time_window_seconds: int = CORRELATION_TIME_WINDOW_SECONDS,
) -> bool:
    """Check if an event falls within the correlation window of an existing incident."""
    if existing_incident_time is None or event_time is None:
        return False
    delta = abs((event_time - existing_incident_time).total_seconds())
    return delta <= time_window_seconds


def compute_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Haversine distance between two GPS coordinates in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cameras_spatially_correlated(
    cam1_lat: float, cam1_lon: float,
    cam2_lat: float, cam2_lon: float,
    max_distance: float = CORRELATION_DISTANCE_METERS,
) -> bool:
    """Check if two cameras are within spatial correlation distance."""
    if cam1_lat == 0 and cam1_lon == 0:
        return True  # Unknown location → always try temporal correlation
    if cam2_lat == 0 and cam2_lon == 0:
        return True
    dist = compute_distance_meters(cam1_lat, cam1_lon, cam2_lat, cam2_lon)
    return dist <= max_distance


def build_correlation_key(
    event_type: str,
    object_type: str,
    zone_name: str,
    time_bucket_minutes: int = 5,
    occurred_at: datetime | None = None,
) -> str:
    """Build a deduplication/correlation fingerprint for an event.

    Events with the same key in the same time bucket are candidates for correlation.
    """
    ts = occurred_at or datetime.utcnow()
    bucket = ts.strftime(f"%Y%m%d%H{time_bucket_minutes}")
    return f"{event_type}:{object_type}:{zone_name}:{bucket}"


def correlate_incidents(
    existing_incidents: list[dict[str, Any]],
    new_event: dict[str, Any],
    camera_lat: float = 0.0,
    camera_lon: float = 0.0,
) -> str | None:
    """Find an existing incident to correlate with, or None.

    Returns the incident_code of the correlated incident.
    """
    for inc in existing_incidents:
        if inc.get("status") in ("CLOSED",):
            continue
        inc_time = inc.get("created_at")
        event_time = new_event.get("occurred_at")
        if inc_time and event_time:
            if not should_correlate(inc_time, event_time):
                continue
        # Check object type similarity
        if inc.get("object_type", "") == new_event.get("object_type", ""):
            return inc.get("incident_code")
    return None
