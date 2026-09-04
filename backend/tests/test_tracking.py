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


def test_occlusion_same_track_id_retained():
    """OCCLUSION: Track ID persists through a brief disappearance (≤ max_disappeared frames).

    Simulates an object going behind a pole for 5 frames, then reappearing
    at the same position. The same track_id MUST be reused (not a new one).
    """
    tracker = CentroidTracker(max_disappeared=10)
    # Frame 1: object appears at (100, 100)-(200, 200)
    det = _make_detection(100, 100, 200, 200)
    tracks = tracker.update([det], datetime(2024, 1, 1, 0, 0, 0))
    original_track_id = tracks[0].track_id

    # Frames 2-6: object disappears (behind pole) — 5 frames, under max_disappeared (10)
    for i in range(1, 6):
        active = tracker.update([], datetime(2024, 1, 1, 0, 0, i))

    # The track should still be alive (occluded but not evicted)
    active_ids = {t.track_id for t in active}
    assert original_track_id in active_ids, (
        f"Track {original_track_id} should survive {5} disappeared frames (max_disappeared=10)"
    )

    # Frame 7: object reappears at same position
    det_reappear = _make_detection(100, 100, 200, 200)
    tracks_after = tracker.update([det_reappear], datetime(2024, 1, 1, 0, 0, 6))

    reappear_id = tracks_after[0].track_id
    assert reappear_id == original_track_id, (
        f"Expected same track_id={original_track_id} after reappearance, got {reappear_id}. "
        f"The tracker must NOT create a new ID for a briefly occluded object."
    )


def test_far_reappearance_creates_new_track():
    """OCCLUSION: Object disappearing then reappearing far away gets a NEW track ID.

    Simulates: object exits frame, a completely different object appears far away.
    The tracker must NOT recycle the old track_id — that would cause false associations.
    """
    tracker = CentroidTracker(max_disappeared=10)
    # Frame 1: object at top-left
    det = _make_detection(10, 10, 60, 60)
    tracks = tracker.update([det], datetime(2024, 1, 1, 0, 0, 0))
    original_id = tracks[0].track_id

    # Frames 2-12: object disappears for 11 frames (> max_disappeared=10)
    for i in range(1, 12):
        tracker.update([], datetime(2024, 1, 1, 0, 0, i))

    # Frame 13: completely different object appears far away (bottom-right)
    det_new = _make_detection(800, 600, 900, 700)
    tracks_new = tracker.update([det_new], datetime(2024, 1, 1, 0, 0, 12))

    assert len(tracks_new) == 1
    new_id = tracks_new[0].track_id
    assert new_id != original_id, (
        f"Expected NEW track_id after {11} disappeared frames (max_disappeared=10), "
        f"but got recycled id={new_id}."
    )
