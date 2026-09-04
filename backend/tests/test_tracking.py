"""Tests for the Centroid/IoU object tracker."""

from datetime import datetime

from edge.tracking.centroid import CentroidTracker, TrackedObject
from edge.detection.base import Detection


def _make_detection(x1, y1, x2, y2, label="person", confidence=0.9):
    return Detection(label=label, confidence=confidence, bbox=(x1, y1, x2, y2))


def test_empty_frame():
    """No detections should produce no active tracks."""
    tracker = CentroidTracker()
    tracks = tracker.update([], datetime.utcnow())
    assert len(tracks) == 0


def test_single_detection_creates_track():
    """First detection should create a new track."""
    tracker = CentroidTracker()
    det = _make_detection(100, 100, 200, 200)
    tracks = tracker.update([det], datetime.utcnow())
    assert len(tracks) == 1
    assert tracks[0].track_id.startswith("T-")
    assert tracks[0].label == "person"


def test_two_detections_different_positions():
    """Two far-apart detections should create two tracks."""
    tracker = CentroidTracker()
    det1 = _make_detection(50, 50, 100, 100)
    det2 = _make_detection(400, 400, 500, 500)
    tracks = tracker.update([det1, det2], datetime.utcnow())
    assert len(tracks) == 2


def test_tracking_persistence():
    """Same object across frames should maintain the same ID (overlapping boxes)."""
    tracker = CentroidTracker()
    # Frame 1: box at (100,100)-(200,200)
    det = _make_detection(100, 100, 200, 200)
    t1 = tracker.update([det], datetime(2024, 1, 1, 0, 0, 0))
    # Frame 2: box shifted slightly (overlaps with frame 1 box)
    det2 = _make_detection(105, 105, 205, 205)
    t2 = tracker.update([det2], datetime(2024, 1, 1, 0, 0, 1))
    assert t1[0].track_id == t2[0].track_id


def test_dwell_time_increases():
    """Dwell time should increase across frames."""
    tracker = CentroidTracker()
    det = _make_detection(100, 100, 200, 200)
    t1 = tracker.update([det], datetime(2024, 1, 1, 0, 0, 0))
    # Shift slightly so IoU still matches
    det2 = _make_detection(108, 108, 208, 208)
    t2 = tracker.update([det2], datetime(2024, 1, 1, 0, 0, 5))
    assert t2[0].dwell_time_seconds >= 4


def test_track_inactive_after_disappearance():
    """Track should become inactive after max_disappeared frames."""
    tracker = CentroidTracker(max_disappeared=3)
    det = _make_detection(100, 100, 200, 200)
    tracker.update([det], datetime(2024, 1, 1, 0, 0, 0))

    # 4 frames with no detections
    for i in range(1, 6):
        tracker.update([], datetime(2024, 1, 1, 0, 0, i))

    active = tracker.get_active_tracks()
    assert len(active) == 0


def test_direction_estimation():
    """Tracker should estimate movement direction (overlapping boxes)."""
    tracker = CentroidTracker()
    # Move rightward with overlapping boxes
    d1 = _make_detection(100, 100, 200, 200)
    tracker.update([d1], datetime(2024, 1, 1, 0, 0, 0))
    d2 = _make_detection(130, 100, 230, 200)
    tracks = tracker.update([d2], datetime(2024, 1, 1, 0, 0, 1))
    assert tracks[0].direction == "EAST"


def test_speed_estimation():
    """Tracker should estimate speed (overlapping boxes)."""
    tracker = CentroidTracker()
    d1 = _make_detection(100, 100, 200, 200)
    tracker.update([d1], datetime(2024, 1, 1, 0, 0, 0))
    d2 = _make_detection(120, 120, 220, 220)
    tracks = tracker.update([d2], datetime(2024, 1, 1, 0, 0, 2))
    assert tracks[0].speed_estimate > 0


def test_to_dict():
    """TrackedObject should serialize to dict."""
    tracker = CentroidTracker()
    det = _make_detection(100, 100, 200, 200)
    tracks = tracker.update([det], datetime.utcnow())
    d = tracks[0].to_dict()
    assert "track_id" in d
    assert "label" in d
    assert "active" in d
    assert "trajectory" in d
