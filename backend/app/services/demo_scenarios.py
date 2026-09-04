"""
Demo Scenario Engine.

Provides multiple reproducible demo scenarios for SIH presentation.
Each scenario generates a deterministic sequence of events, detections,
tracks, incidents, alerts, and evidence.

Scenarios:
1. Restricted zone intrusion
2. Night movement
3. Loitering
4. Vehicle near restricted zone
5. Abandoned object
6. Camera outage
7. Offline edge mode
8. Multi-camera correlated incident
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any

from backend.app.services.scoring import compute_threat_score


SCENARIOS: dict[str, dict[str, Any]] = {
    "intrusion": {
        "id": "intrusion",
        "name": "Restricted Zone Intrusion",
        "description": "Person enters restricted border zone and triggers multi-signal alert.",
        "severity": "CRITICAL",
        "events": [
            {"type": "detection", "object": "person", "t_offset": 0, "confidence": 0.88,
             "bbox": [320, 200, 420, 400]},
            {"type": "zone_entry", "object": "person", "t_offset": 5, "confidence": 0.91,
             "zone": "Restricted Perimeter", "bbox": [350, 210, 450, 410]},
            {"type": "zone_crossing", "object": "person", "t_offset": 8, "confidence": 0.93,
             "zone": "Restricted Perimeter", "bbox": [380, 220, 480, 420]},
            {"type": "loitering", "object": "person", "t_offset": 25, "confidence": 0.82,
             "zone": "Restricted Perimeter", "dwell_seconds": 35},
        ],
        "signals": {"confidence": 1.0, "zone_severity": 1.0, "boundary_crossing": 1.0,
                    "loitering": 1.0, "night": 0.4, "vehicle_context": 0.0,
                    "behavior_anomaly": 1.0, "repeated_activity": 1.0,
                    "camera_health_degraded": 0.0, "cross_camera_corroboration": 0.0},
        "timeline_events": [
            (0, "detection", "Person detected approaching perimeter"),
            (5, "zone_entry", "Entered restricted zone"),
            (8, "zone_crossing", "Crossed restricted zone boundary"),
            (25, "loitering", "Loitering threshold exceeded (35 seconds)"),
        ],
    },
    "night_movement": {
        "id": "night_movement",
        "name": "Night-Time Movement",
        "description": "Suspicious movement detected during night hours.",
        "severity": "HIGH",
        "events": [
            {"type": "detection", "object": "person", "t_offset": 0, "confidence": 0.76,
             "bbox": [500, 250, 580, 420]},
            {"type": "zone_entry", "object": "person", "t_offset": 3, "confidence": 0.78,
             "zone": "Monitoring Zone", "bbox": [510, 260, 590, 430]},
        ],
        "signals": {"confidence": 0.76, "zone_severity": 0.4, "boundary_crossing": 0.0,
                    "loitering": 0.0, "night": 1.0, "behavior_anomaly": 0.5},
        "timeline_events": [
            (0, "detection", "Movement detected — night context active"),
            (3, "zone_entry", "Entered monitoring zone"),
        ],
    },
    "loitering": {
        "id": "loitering",
        "name": "Extended Loitering",
        "description": "Object remains stationary near boundary for extended period.",
        "severity": "MEDIUM",
        "events": [
            {"type": "detection", "object": "person", "t_offset": 0, "confidence": 0.85,
             "bbox": [400, 300, 480, 450]},
            {"type": "zone_entry", "object": "person", "t_offset": 2, "confidence": 0.87,
             "zone": "Patrol Zone", "bbox": [405, 305, 485, 455]},
            {"type": "loitering", "object": "person", "t_offset": 65, "confidence": 0.90,
             "zone": "Patrol Zone", "dwell_seconds": 90},
        ],
        "signals": {"confidence": 0.85, "zone_severity": 0.3, "boundary_crossing": 0.0,
                    "loitering": 1.0, "night": 0.0, "behavior_anomaly": 0.4},
        "timeline_events": [
            (0, "detection", "Person detected"),
            (2, "zone_entry", "Entered patrol zone"),
            (65, "loitering", "Stationary for 90 seconds"),
        ],
    },
    "vehicle": {
        "id": "vehicle",
        "name": "Vehicle Near Restricted Zone",
        "description": "Vehicle detected approaching restricted perimeter.",
        "severity": "HIGH",
        "events": [
            {"type": "detection", "object": "vehicle", "t_offset": 0, "confidence": 0.92,
             "bbox": [100, 350, 350, 500]},
            {"type": "zone_entry", "object": "vehicle", "t_offset": 4, "confidence": 0.94,
             "zone": "Restricted Perimeter", "bbox": [120, 355, 370, 505]},
        ],
        "signals": {"confidence": 0.92, "zone_severity": 0.9, "boundary_crossing": 0.5,
                    "loitering": 0.0, "night": 0.0, "vehicle_context": 1.0, "behavior_anomaly": 0.3},
        "timeline_events": [
            (0, "detection", "Vehicle detected approaching zone"),
            (4, "zone_entry", "Vehicle entered restricted perimeter area"),
        ],
    },
    "abandoned": {
        "id": "abandoned",
        "name": "Abandoned Object",
        "description": "Object left stationary after person departs.",
        "severity": "HIGH",
        "events": [
            {"type": "detection", "object": "person", "t_offset": 0, "confidence": 0.89,
             "bbox": [450, 280, 530, 430]},
            {"type": "detection", "object": "object", "t_offset": 0, "confidence": 0.75,
             "bbox": [460, 380, 520, 430]},
            {"type": "abandoned_object", "object": "object", "t_offset": 55, "confidence": 0.80,
             "stationary_seconds": 60, "bbox": [460, 380, 520, 430]},
        ],
        "signals": {"confidence": 0.80, "zone_severity": 0.3, "boundary_crossing": 0.0,
                    "loitering": 0.0, "night": 0.0, "behavior_anomaly": 0.9},
        "timeline_events": [
            (0, "detection", "Person with object detected"),
            (55, "abandoned_object", "Object stationary for 60 seconds after person departed"),
        ],
    },
    "camera_outage": {
        "id": "camera_outage",
        "name": "Camera Outage",
        "description": "Camera goes offline or degrades significantly.",
        "severity": "MEDIUM",
        "events": [
            {"type": "camera_health", "object": "camera", "t_offset": 0, "confidence": 0.5,
             "health_score": 35, "status": "DEGRADED"},
        ],
        "signals": {"confidence": 0.5, "camera_health_degraded": 1.0},
        "timeline_events": [
            (0, "camera_health", "Camera health degraded — low frame quality"),
        ],
    },
    "multi_camera": {
        "id": "multi_camera",
        "name": "Multi-Camera Correlated",
        "description": "Events correlated across multiple cameras.",
        "severity": "CRITICAL",
        "events": [
            {"type": "detection", "object": "person", "t_offset": 0, "confidence": 0.88,
             "bbox": [300, 200, 400, 400], "camera_id": 1},
            {"type": "zone_crossing", "object": "person", "t_offset": 5, "confidence": 0.91,
             "zone": "Restricted Perimeter", "camera_id": 1},
            {"type": "detection", "object": "person", "t_offset": 18, "confidence": 0.82,
             "bbox": [200, 180, 300, 380], "camera_id": 2},
            {"type": "detection", "object": "vehicle", "t_offset": 25, "confidence": 0.85,
             "bbox": [50, 300, 250, 450], "camera_id": 3},
        ],
        "signals": {"confidence": 0.88, "zone_severity": 1.0, "boundary_crossing": 1.0,
                    "loitering": 0.0, "night": 0.0, "behavior_anomaly": 0.8,
                    "cross_camera_corroboration": 1.0, "vehicle_context": 0.5},
        "timeline_events": [
            (0, "detection", "Person detected — Camera BOP-01"),
            (5, "zone_crossing", "Zone crossing — Camera BOP-01"),
            (18, "detection", "Similar movement pattern — Camera BOP-02"),
            (25, "detection", "Vehicle detected near exit — Camera BOP-03"),
        ],
    },
}


def get_available_scenarios() -> list[dict[str, Any]]:
    """Return list of available demo scenarios."""
    return [
        {"id": s["id"], "name": s["name"], "description": s["description"],
         "severity": s["severity"]}
        for s in SCENARIOS.values()
    ]


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    """Get a specific scenario by ID."""
    return SCENARIOS.get(scenario_id)


def generate_scenario_events(
    scenario_id: str,
    base_time: datetime | None = None,
    camera_id: int = 1,
) -> dict[str, Any]:
    """Generate a complete event set for a scenario.

    Returns a dict with: scenario info, generated events, threat assessment, and timeline.
    """
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        scenario = SCENARIOS["intrusion"]

    base = base_time or datetime.utcnow()

    # Generate events with timestamps and real WGS84 Geo-Registration
    from backend.app.services.georegistration import project_pixel_to_gps

    events = []
    first_geo = None
    for evt_def in scenario["events"]:
        payload = {k: v for k, v in evt_def.items()
                   if k not in ("type", "object", "t_offset", "confidence", "camera_id")}

        # If bounding box is present, project foot to real-world GPS
        if "bbox" in evt_def:
            bx1, by1, bx2, by2 = evt_def["bbox"]
            foot_x = (bx1 + bx2) / 2.0
            foot_y = float(by2)
            geo = project_pixel_to_gps(
                pixel_x=foot_x,
                pixel_y=foot_y,
                camera_lat=28.6139,
                camera_lon=77.2090,
                camera_height_m=12.0,
                tilt_deg=15.0,
                heading_deg=35.0,
            )
            payload.update(geo)
            if not first_geo:
                first_geo = geo

        evt = {
            "event_type": evt_def["type"],
            "object_type": evt_def["object"],
            "confidence": evt_def["confidence"],
            "occurred_at": (base + timedelta(seconds=evt_def["t_offset"])).isoformat(),
            "camera_id": evt_def.get("camera_id", camera_id),
            "payload": payload,
        }
        events.append(evt)

    # Compute threat assessment
    assessment = compute_threat_score(scenario["signals"])

    # Build timeline
    timeline = []
    for t_offset, etype, desc in scenario.get("timeline_events", []):
        timeline.append({
            "timestamp": (base + timedelta(seconds=t_offset)).isoformat(),
            "event_type": etype,
            "description": desc,
            "source": "ai_perception" if "detection" in etype else "context_engine",
        })

    return {
        "scenario": scenario,
        "events": events,
        "threat_assessment": {
            "score": assessment.score,
            "severity": assessment.severity,
            "confidence": assessment.confidence,
            "reasons": assessment.reasons,
            "recommended_action": assessment.recommended_action,
            "ai_assessment": assessment.ai_assessment,
            "target_geo": first_geo,
        },
        "timeline": timeline,
    }
