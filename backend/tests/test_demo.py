"""Tests for demo scenario engine."""

from datetime import datetime
from backend.app.services.demo_scenarios import (
    get_available_scenarios, generate_scenario_events,
    get_scenario, SCENARIOS,
)


def test_list_scenarios():
    """Should list all available scenarios."""
    scenarios = get_available_scenarios()
    assert len(scenarios) >= 6
    ids = [s["id"] for s in scenarios]
    assert "intrusion" in ids
    assert "night_movement" in ids


def test_generate_intrusion_scenario():
    """Intrusion scenario should produce CRITICAL severity."""
    result = generate_scenario_events("intrusion")
    assert result["threat_assessment"]["severity"] == "CRITICAL"
    assert len(result["events"]) > 0
    assert len(result["timeline"]) > 0


def test_generate_night_scenario():
    """Night scenario should include night signal."""
    result = generate_scenario_events("night_movement")
    assert result["threat_assessment"]["score"] > 0
    # Should have night-related assessment
    signals = result["scenario"]["signals"]
    assert signals.get("night", 0) > 0


def test_generate_vehicle_scenario():
    """Vehicle scenario should detect vehicle context."""
    result = generate_scenario_events("vehicle")
    signals = result["scenario"]["signals"]
    assert signals.get("vehicle_context", 0) == 1.0


def test_generate_multi_camera():
    """Multi-camera scenario should have events from multiple cameras."""
    result = generate_scenario_events("multi_camera")
    cameras = set()
    for evt in result["events"]:
        cameras.add(evt.get("camera_id", 0))
    assert len(cameras) >= 2


def test_unknown_scenario_falls_back():
    """Unknown scenario ID should fall back to intrusion."""
    result = generate_scenario_events("nonexistent")
    assert result["scenario"]["id"] == "intrusion"


def test_timeline_has_timestamps():
    """All timeline events should have timestamps."""
    result = generate_scenario_events("intrusion")
    for evt in result["timeline"]:
        assert "timestamp" in evt
        assert "event_type" in evt
        assert "description" in evt


def test_threat_assessment_structure():
    """Assessment should have all required fields."""
    result = generate_scenario_events("loitering")
    ta = result["threat_assessment"]
    assert "score" in ta
    assert "severity" in ta
    assert "confidence" in ta
    assert "reasons" in ta
    assert "recommended_action" in ta


def test_all_scenarios_generate_events():
    """Every scenario should produce at least one event."""
    for scenario_id in SCENARIOS:
        result = generate_scenario_events(scenario_id)
        assert len(result["events"]) > 0, f"Scenario '{scenario_id}' produced no events"
