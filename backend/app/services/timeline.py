"""
Incident Timeline Service.

Manages the chronological event timeline for each incident,
showing detection → zone entry → behavior → scoring → alert → operator actions.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any


def create_timeline_event(
    event_type: str,
    description: str,
    source: str = "system",
    confidence: float | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a single timeline entry."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "description": description,
        "source": source,
        "confidence": confidence,
        "payload": payload or {},
    }


def append_timeline(timeline: list[dict], event: dict) -> list[dict]:
    """Append an event to an incident timeline."""
    timeline.append(event)
    return timeline


def build_incident_timeline(
    events: list[dict[str, Any]],
    incident_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build a full incident timeline from events and incident metadata."""
    timeline = []

    # Sort events chronologically
    sorted_events = sorted(events, key=lambda e: e.get("occurred_at", ""))

    for evt in sorted_events:
        etype = evt.get("event_type", "unknown")
        desc = _describe_event(evt)
        confidence = evt.get("confidence")
        timeline.append(create_timeline_event(
            event_type=etype,
            description=desc,
            source="ai_perception",
            confidence=confidence,
            payload={"event_id": evt.get("id"), "object_type": evt.get("object_type")},
        ))

    # Add scoring event
    if incident_data.get("threat_score", 0) > 0:
        timeline.append(create_timeline_event(
            event_type="threat_score_updated",
            description=f"Threat score: {incident_data['threat_score']}/100 "
                        f"(severity: {incident_data.get('severity', 'LOW')})",
            source="scoring_engine",
        ))

    # Add alert event
    timeline.append(create_timeline_event(
        event_type="alert_generated",
        description="Alert generated for operator review",
        source="alert_engine",
    ))

    # Add operator actions if present
    if incident_data.get("acknowledged_at"):
        timeline.append(create_timeline_event(
            event_type="operator_acknowledged",
            description=f"Acknowledged by {incident_data.get('acknowledged_by', 'operator')}",
            source="operator",
        ))

    if incident_data.get("escalated_at"):
        timeline.append(create_timeline_event(
            event_type="incident_escalated",
            description=f"Escalated by {incident_data.get('escalated_by', 'operator')}",
            source="operator",
        ))

    if incident_data.get("closed_at"):
        timeline.append(create_timeline_event(
            event_type="incident_closed",
            description=f"Closed by {incident_data.get('closed_by', 'operator')}",
            source="operator",
        ))

    return timeline


def _describe_event(evt: dict) -> str:
    """Generate a human-readable description of an event."""
    etype = evt.get("event_type", "unknown")
    obj = evt.get("object_type", "object")
    zone = evt.get("payload", {}).get("zone_name", "")
    descriptions = {
        "detection": f"{obj.capitalize()} detected",
        "zone_crossing": f"{obj.capitalize()} crossed into {zone or 'restricted zone'}",
        "zone_entry": f"{obj.capitalize()} entered {zone or 'zone'}",
        "zone_exit": f"{obj.capitalize()} exited {zone or 'zone'}",
        "loitering": f"{obj.capitalize()} loitering detected in {zone or 'zone'}",
        "abandoned_object": f"Stationary object detected near {zone or 'zone'}",
        "direction_violation": f"{obj.capitalize()} moved in wrong direction",
        "rapid_movement": f"Rapid movement detected",
        "camera_health": "Camera health event",
    }
    return descriptions.get(etype, etype.replace("_", " ").title())
