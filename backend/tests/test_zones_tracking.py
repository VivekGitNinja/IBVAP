"""
Unit and Integration Tests for Phase 1:
- Multi-object tracking persistence and stability
- Zone CRUD API and validation rejections (HTTP 422)
- Virtual fence crossing / intrusion engine (directional tripwires, perimeter entry, cooldown)
- Armed schedule and night-only filtering
- Deterministic behavior rule engine (loitering, crowd gathering, rapid movement)
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.zone import Zone
from backend.app.models.user import User
from backend.app.core.security import create_access_token
from edge.detection.base import Detection
from edge.tracking.centroid import CentroidTracker, TrackedObject
from edge.zones.fence import ZoneFence


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token("admin", "ADMIN")
    return {"Authorization": f"Bearer {token}"}



# ── TASK 1.1: TRACKER STABILITY & SUMMARY ──────────────────────────

def test_tracker_stable_id_and_summary():
    tracker = CentroidTracker(iou_threshold=0.3)
    
    # Frame 1: Object appears at (100, 100, 150, 150)
    d1 = [Detection(label="person", class_name="person", confidence=0.9, bbox=(100, 100, 150, 150), frame_id=1)]
    tracker.update(d1, frame_time=datetime(2026, 9, 4, 12, 0, 0))
    tid1 = d1[0].track_id
    assert tid1 is not None
    assert tid1.startswith("T-")
    
    # Frame 2: Object moves slightly to (105, 105, 155, 155)
    d2 = [Detection(label="person", class_name="person", confidence=0.88, bbox=(105, 105, 155, 155), frame_id=2)]
    tracker.update(d2, frame_time=datetime(2026, 9, 4, 12, 0, 1))
    assert d2[0].track_id == tid1
    
    # Frame 3: Object moves again to (110, 110, 160, 160)
    d3 = [Detection(label="person", class_name="person", confidence=0.85, bbox=(110, 110, 160, 160), frame_id=3)]
    tracker.update(d3, frame_time=datetime(2026, 9, 4, 12, 0, 2))
    assert d3[0].track_id == tid1

    summaries = tracker.get_track_summaries()
    assert tid1 in summaries
    s = summaries[tid1]
    assert s["class"] == "person"
    assert s["first_frame"] == 1
    assert s["last_frame"] == 3
    assert s["frame_count"] == 3
    assert s["total_distance"] > 0


# ── TASK 1.2: ZONE MODEL & CRUD VALIDATION ─────────────────────────

def test_zone_crud_lifecycle(client, auth_headers):
    # 1. Create Line Tripwire Zone
    line_payload = {
        "name": "Sector 4 Tripwire",
        "zone_type": "RESTRICTED",
        "geometry": {
            "type": "line",
            "points": [[0.2, 0.0], [0.2, 1.0]]
        },
        "direction": "a_to_b",
        "severity": 0.85,
        "min_confidence": 0.30
    }
    r_create = client.post("/api/v1/zones", json=line_payload, headers=auth_headers)
    assert r_create.status_code == 201, r_create.text
    z_data = r_create.json()
    assert z_data["id"] > 0
    assert z_data["direction"] == "a_to_b"
    assert z_data["geometry"]["type"] == "line"
    zone_id = z_data["id"]

    # 2. Get Zone
    r_get = client.get(f"/api/v1/zones/{zone_id}", headers=auth_headers)
    assert r_get.status_code == 200
    assert r_get.json()["name"] == "Sector 4 Tripwire"

    # 3. Patch Zone
    r_patch = client.patch(f"/api/v1/zones/{zone_id}", json={"name": "Sector 4 Updated", "min_confidence": 0.45}, headers=auth_headers)
    assert r_patch.status_code == 200
    assert r_patch.json()["name"] == "Sector 4 Updated"
    assert r_patch.json()["min_confidence"] == 0.45

    # 4. Delete Zone
    r_del = client.delete(f"/api/v1/zones/{zone_id}", headers=auth_headers)
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True

    # 5. Verify 404
    r_check = client.get(f"/api/v1/zones/{zone_id}", headers=auth_headers)
    assert r_check.status_code == 404


def test_zone_validation_rejections(client, auth_headers):
    # Rejection 1: Line with < 2 points
    r1 = client.post("/api/v1/zones", json={
        "name": "Invalid Line",
        "geometry": {"type": "line", "points": [[0.5, 0.5]]}
    }, headers=auth_headers)
    assert r1.status_code == 422

    # Rejection 2: Polygon with < 3 points
    r2 = client.post("/api/v1/zones", json={
        "name": "Invalid Poly",
        "geometry": {"type": "polygon", "points": [[0.1, 0.1], [0.2, 0.2]]}
    }, headers=auth_headers)
    assert r2.status_code == 422

    # Rejection 3: Coordinates > 1.0
    r3 = client.post("/api/v1/zones", json={
        "name": "Out of bounds",
        "geometry": {"type": "line", "points": [[0.0, 0.0], [1.5, 0.5]]}
    }, headers=auth_headers)
    assert r3.status_code == 422

    # Rejection 4: Invalid direction enum
    r4 = client.post("/api/v1/zones", json={
        "name": "Bad direction",
        "geometry": {"type": "line", "points": [[0.0, 0.0], [0.5, 0.5]]},
        "direction": "diagonal"
    }, headers=auth_headers)
    assert r4.status_code == 422

    # Rejection 5: Invalid confidence (> 1.0)
    r5 = client.post("/api/v1/zones", json={
        "name": "Bad confidence",
        "geometry": {"type": "line", "points": [[0.0, 0.0], [0.5, 0.5]]},
        "min_confidence": 1.5
    }, headers=auth_headers)
    assert r5.status_code == 422


# ── TASK 1.3: CROSSING & INTRUSION ENGINE ──────────────────────────

def test_line_crossing_and_directionality():
    # Vertical line at x=500, pointing (500, 0) to (500, 1000)
    # Side A is left (x < 500), Side B is right (x > 500)
    zone_a_to_b = {
        "id": 101,
        "name": "Line Fence A->B",
        "zone_type": "RESTRICTED",
        "geometry": {"type": "line", "points": [[500, 0], [500, 1000]]},
        "direction": "a_to_b",
        "severity": 0.9,
    }
    fence = ZoneFence([zone_a_to_b], default_cooldown_seconds=5.0)

    # Frame 1: Object at x=450 (left of fence)
    t0 = datetime(2026, 9, 4, 12, 0, 0)
    ev0 = fence.check_position("T-1", (450, 500), frame_time=t0)
    assert len(ev0) == 0

    # Frame 2: Object crosses to x=550 (left to right -> a_to_b)
    t1 = datetime(2026, 9, 4, 12, 0, 1)
    ev1 = fence.check_position("T-1", (550, 500), frame_time=t1)
    assert len(ev1) >= 1
    assert any(e["event_type"] == "zone_intrusion" for e in ev1)
    assert ev1[0]["direction"] == "a_to_b"

    # Frame 3: Next frame still on right side -> duplicate suppressed by cooldown
    t2 = datetime(2026, 9, 4, 12, 0, 2)
    ev2 = fence.check_position("T-1", (560, 500), frame_time=t2)
    assert len(ev2) == 0

    # Now test opposite direction (B to A, right to left) on a_to_b zone
    fence_opp = ZoneFence([zone_a_to_b], default_cooldown_seconds=5.0)
    fence_opp.check_position("T-2", (550, 500), frame_time=t0)
    ev_opp = fence_opp.check_position("T-2", (450, 500), frame_time=t1)
    # Since zone only allows a_to_b, crossing B->A should NOT fire zone_intrusion!
    assert not any(e["event_type"] == "zone_intrusion" for e in ev_opp)


def test_polygon_entry_intrusion():
    zone_poly = {
        "id": 102,
        "name": "Sensitive Bunker",
        "zone_type": "RESTRICTED",
        "geometry": {
            "type": "polygon",
            "points": [[100, 100], [300, 100], [300, 300], [100, 300]]
        },
        "severity": 0.8,
    }
    fence = ZoneFence([zone_poly], default_cooldown_seconds=10.0)

    # Position 1: Outside (50, 50)
    t0 = datetime(2026, 9, 4, 12, 0, 0)
    ev0 = fence.check_position("T-1", (50, 50), frame_time=t0)
    assert len(ev0) == 0

    # Position 2: Inside (200, 200) -> Entry + Intrusion
    t1 = datetime(2026, 9, 4, 12, 0, 1)
    ev1 = fence.check_position("T-1", (200, 200), frame_time=t1)
    assert any(e["event_type"] == "zone_entry" for e in ev1)
    assert any(e["event_type"] == "zone_intrusion" for e in ev1)

    # Position 3: Inside again -> Suppressed by cooldown
    t2 = datetime(2026, 9, 4, 12, 0, 2)
    ev2 = fence.check_position("T-1", (210, 210), frame_time=t2)
    assert not any(e["event_type"] == "zone_intrusion" for e in ev2)


def test_armed_schedule_and_night_only():
    # Zone 1: Armed only on Mondays 08:00 - 18:00
    zone_sched = {
        "id": 103,
        "name": "Office Hours Zone",
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "armed_schedule": {"mon": [["08:00", "18:00"]]},
        "severity": 0.5,
    }
    fence = ZoneFence([zone_sched])

    # Sunday 12:00 -> not armed -> should not fire
    t_sun = datetime(2026, 9, 6, 12, 0, 0) # Sept 6, 2026 is Sunday
    ev_sun = fence.check_position("T-1", (50, 50), frame_time=t_sun)
    assert len(ev_sun) == 0

    # Zone 2: Night only
    zone_night = {
        "id": 104,
        "name": "Night Patrol Zone",
        "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "night_only": True,
        "severity": 0.7,
    }
    fence_night = ZoneFence([zone_night])
    
    # Day frame (is_night=False) -> should not fire
    ev_day = fence_night.check_position("T-1", (50, 50), is_night=False)
    assert len(ev_day) == 0

    # Night frame (is_night=True) -> should fire
    ev_night = fence_night.check_position("T-1", (50, 50), is_night=True)
    assert len(ev_night) >= 1
    assert any(e["event_type"] == "zone_entry" for e in ev_night)


# ── TASK 1.4: BEHAVIOR RULES (LOITERING, CROWD, RAPID) ────────────

def test_behavior_loitering_rule():
    zone = {
        "id": 201,
        "name": "Restricted Depot",
        "geometry": {"type": "polygon", "points": [[0, 0], [500, 0], [500, 500], [0, 500]]},
        "dwell_threshold_seconds": 30,
    }
    fence = ZoneFence([zone], loitering_seconds=30.0, default_cooldown_seconds=10.0)

    t0 = datetime(2026, 9, 4, 12, 0, 0)
    fence.check_position("T-1", (250, 250), frame_time=t0)

    track_obj = TrackedObject(
        track_id="T-1",
        label="person",
        last_bbox={"x1": 240, "y1": 240, "x2": 260, "y2": 260},
        active=True
    )

    # At 20s: under 30s threshold -> no loitering event
    t_20s = t0 + timedelta(seconds=20)
    bev_20 = fence.check_behaviors([track_obj], frame_time=t_20s)
    assert not any(e["event_type"] == "loitering" for e in bev_20)

    # At 35s: exceeds 30s threshold -> triggers loitering
    t_35s = t0 + timedelta(seconds=35)
    bev_35 = fence.check_behaviors([track_obj], frame_time=t_35s)
    loiter_events = [e for e in bev_35 if e["event_type"] == "loitering"]
    assert len(loiter_events) == 1
    assert loiter_events[0]["track_id"] == "T-1"
    assert loiter_events[0]["dwell_seconds"] >= 30.0


def test_behavior_crowd_gathering_rule():
    zone = {
        "id": 202,
        "name": "Gate Area",
        "geometry": {"type": "polygon", "points": [[0, 0], [500, 0], [500, 500], [0, 500]]},
        "crowd_threshold": 4,
    }
    fence = ZoneFence([zone], crowd_min_count=4, crowd_window_seconds=30.0, default_cooldown_seconds=10.0)

    t0 = datetime(2026, 9, 4, 12, 0, 0)
    
    # 3 people enter zone
    for i in range(1, 4):
        fence.check_position(f"T-{i}", (100 + i * 20, 100), frame_time=t0)
    
    tracks_3 = [
        TrackedObject(track_id=f"T-{i}", label="person", active=True)
        for i in range(1, 4)
    ]
    # 3 tracks < 4 threshold -> no crowd alert
    bev_3 = fence.check_behaviors(tracks_3, frame_time=t0)
    assert not any(e["event_type"] == "crowd_gathering" for e in bev_3)

    # 4th person enters zone
    fence.check_position("T-4", (180, 100), frame_time=t0)
    tracks_4 = tracks_3 + [TrackedObject(track_id="T-4", label="person", active=True)]
    
    # 4 tracks >= 4 threshold -> triggers crowd alert
    bev_4 = fence.check_behaviors(tracks_4, frame_time=t0)
    crowd_events = [e for e in bev_4 if e["event_type"] == "crowd_gathering"]
    assert len(crowd_events) == 1
    assert crowd_events[0]["count"] == 4


def test_behavior_rapid_movement_rule():
    fence = ZoneFence(rapid_speed_threshold=150.0, default_cooldown_seconds=10.0)
    t0 = datetime(2026, 9, 4, 12, 0, 0)

    # Track moving at 50 px/s -> normal
    normal_track = TrackedObject(
        track_id="T-NORMAL",
        label="person",
        speed_estimate=50.0,
        last_bbox={"x1": 100, "y1": 100, "x2": 140, "y2": 180},
        active=True
    )
    bev_normal = fence.check_behaviors([normal_track], frame_time=t0)
    assert not any(e["event_type"] == "rapid_movement" for e in bev_normal)

    # Track moving at 220 px/s -> rapid
    rapid_track = TrackedObject(
        track_id="T-RAPID",
        label="person",
        speed_estimate=220.0,
        last_bbox={"x1": 100, "y1": 100, "x2": 140, "y2": 180},
        active=True
    )
    bev_rapid = fence.check_behaviors([rapid_track], frame_time=t0)
    rapid_events = [e for e in bev_rapid if e["event_type"] == "rapid_movement"]
    assert len(rapid_events) == 1
    assert rapid_events[0]["track_id"] == "T-RAPID"
    assert rapid_events[0]["speed"] == 220.0
