"""Tests for the zone fence engine."""

from datetime import datetime
from edge.zones.fence import ZoneFence


def _make_zone(zone_id=1, name="Restricted", zone_type="RESTRICTED",
               polygon=None, severity=1.0):
    if polygon is None:
        polygon = [[100, 100], [400, 100], [400, 400], [100, 400]]
    return {
        "id": zone_id,
        "name": name,
        "zone_type": zone_type,
        "polygon": polygon,
        "severity": severity,
        "dwell_threshold_seconds": 30,
    }


def test_position_inside_zone():
    """Position inside zone should be detected."""
    fence = ZoneFence([_make_zone()])
    result = fence.check_position("T-001", (200, 200))
    assert len(result) >= 1
    event_types = [e["event_type"] for e in result]
    assert "zone_entry" in event_types


def test_position_outside_zone():
    """Position outside zone should not trigger events."""
    fence = ZoneFence([_make_zone()])
    result = fence.check_position("T-001", (500, 500))
    assert len(result) == 0


def test_zone_exit():
    """Moving from inside to outside should trigger zone_exit."""
    fence = ZoneFence([_make_zone()])
    fence.check_position("T-001", (200, 200))
    result = fence.check_position("T-001", (500, 500))
    assert any(e["event_type"] == "zone_exit" for e in result)


def test_restricted_zone_crossing():
    """Entering a restricted zone should emit both entry and crossing."""
    fence = ZoneFence([_make_zone(zone_type="RESTRICTED")])
    result = fence.check_position("T-001", (200, 200))
    event_types = [e["event_type"] for e in result]
    assert "zone_entry" in event_types
    assert "zone_crossing" in event_types


def test_monitoring_zone_no_crossing():
    """Entering a monitoring zone should NOT emit a crossing event."""
    fence = ZoneFence([_make_zone(zone_type="MONITORING")])
    result = fence.check_position("T-001", (200, 200))
    event_types = [e["event_type"] for e in result]
    assert "zone_entry" in event_types
    assert "zone_crossing" not in event_types


def test_is_in_restricted_zone():
    """is_in_restricted_zone should detect restricted zone membership."""
    fence = ZoneFence([_make_zone(zone_type="RESTRICTED")])
    assert fence.is_in_restricted_zone((200, 200)) is True
    assert fence.is_in_restricted_zone((500, 500)) is False


def test_multiple_zones():
    """Multiple overlapping zones should all trigger."""
    z1 = _make_zone(zone_id=1, name="Restricted", zone_type="RESTRICTED")
    z2 = _make_zone(zone_id=2, name="Monitoring", zone_type="MONITORING",
                    polygon=[[150, 150], [350, 150], [350, 350], [150, 350]])
    fence = ZoneFence([z1, z2])
    result = fence.check_position("T-001", (250, 250))
    assert len(result) >= 2  # Entry for both zones + crossing for restricted


def test_cleanup_track():
    """cleanup_track should remove track state."""
    fence = ZoneFence([_make_zone()])
    fence.check_position("T-001", (200, 200))
    fence.cleanup_track("T-001")
    # Next check should not remember previous position
    result = fence.check_position("T-001", (200, 200))
    # Should trigger zone_entry again since state was cleaned
    assert any(e["event_type"] == "zone_entry" for e in result)
