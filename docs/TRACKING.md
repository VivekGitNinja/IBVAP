# IBVAP Multi-Object Tracking System
## Technical Reference — SIH 2026 / SSB MHA (PS-26187)

---

## 1. Production Tracker: `CentroidTracker`

**Location:** `backend/app/services/tracker.py`  
**Class:** `CentroidTracker`

IBVAP uses a single, deterministic **Centroid Tracker** for all production multi-object tracking. This is the exclusive tracker used throughout the entire video analysis pipeline, providing consistent trajectory tracking with zero external tracking dependencies.

---

## 2. Algorithmic Formulation

### 2.1 Detection-to-Track Association

Each video frame produces a set of detections:

```
D = { (bbox_1, conf_1, class_1), ..., (bbox_N, conf_N, class_N) }
```

For each detection, the centroid is computed:

```
centroid(bbox) = ((x1 + x2) / 2, (y1 + y2) / 2)
```

Active tracks from the previous frame are maintained in `_tracks: Dict[str, TrackState]`, keyed by `track_id` (format: `T-{N}` or `T-{class}-{N}`).

### 2.2 IoU + Centroid Distance Matching

Matching is a two-step process:

**Step 1 — IoU Greedy Match:** For each existing track, find the detection with the highest Intersection-over-Union (IoU) overlap ≥ 0.3. Matched pairs are confirmed.

```
IoU(A, B) = |A ∩ B| / |A ∪ B|
```

**Step 2 — Centroid Fallback:** Unmatched tracks are associated with unmatched detections by minimum Euclidean centroid distance, subject to a threshold:

```
threshold = max(width, height) × distance_factor
default distance_factor = 0.35
```

This ensures correct re-association even when bounding box overlap is low (e.g., during partial occlusion).

### 2.3 Track Lifecycle

| State | Trigger | Action |
|-------|---------|--------|
| **NEW** | Detection with no matching track | Assign new `track_id`, `age = 1` |
| **ACTIVE** | Detection matched to existing track | Update centroid, bbox, speed, dwell |
| **OCCLUDED** | No detection for `N ≤ max_disappeared` frames | Retain track, `lost_frames += 1` |
| **TERMINATED** | `lost_frames > max_disappeared` (default: **10 frames**) | Remove from active tracks |

The default **10-frame disappearance retention** ensures tracks survive brief occlusions (e.g., a person passing behind a post at 10 FPS = 1 second of tolerance).

### 2.4 Track Re-identification After Disappearance

If a track disappears for ≤ 10 frames, its centroid position is **extrapolated** using the last known velocity vector:

```
centroid_predicted(t) = centroid_last + velocity × (t - t_last)
```

When a detection reappears within the distance threshold of the predicted position, the **same `track_id` is reused**. This guarantees track identity persistence across brief occlusions.

---

## 3. Track State Fields

Each active track (`TrackState`) maintains:

| Field | Type | Description |
|-------|------|-------------|
| `track_id` | `str` | Unique persistent identifier (e.g., `T-42`) |
| `class_name` | `str` | YOLO class label (`person`, `car`, etc.) |
| `centroid` | `(float, float)` | Current (x, y) centroid in pixels |
| `bbox` | `[x1, y1, x2, y2]` | Bounding box in pixels |
| `age` | `int` | Total frames the track has been alive |
| `lost_frames` | `int` | Consecutive frames with no matching detection |
| `velocity` | `(float, float)` | Estimated (vx, vy) pixels/frame |
| `speed_px_per_s` | `float` | Speed in pixels/second (for rapid-movement rule) |
| `dwell_frames` | `int` | Frames spent inside a zone (for loitering rule) |
| `zone_ids` | `List[int]` | Currently active zone IDs this track occupies |

---

## 4. Virtual Fence Integration

The `ZoneCrossingEngine` (`backend/app/services/zone_engine.py`) consumes active tracks from `CentroidTracker`:

- **Line zones:** Fires `zone_intrusion` when the centroid path segment `(prev_centroid → curr_centroid)` intersects the zone line segment. Direction is checked per zone config (`either / a_to_b / b_to_a`).
- **Polygon zones:** Fires on centroid transition `outside → inside` (using point-in-polygon test).
- **Cooldown:** Per `(track_id, zone_id)` pair (default 10 seconds) to suppress duplicate events.

---

## 5. Performance Characteristics

| Metric | Value |
|--------|-------|
| Max concurrent tracks | ~200 (limited by quadratic distance computation) |
| Processing overhead | < 1 ms per frame at 200 tracks (pure NumPy) |
| Re-ID window | 10 frames (configurable via `max_disappeared`) |
| Distance threshold | 35% of bounding box diagonal |

---

## 6. Known Constraints

1. **No appearance embedding** — track identity is based purely on spatial proximity, not visual similarity. Identical-looking objects that cross paths may swap IDs after close proximity.
2. **Single-camera** — tracks do not persist across camera boundaries (no cross-camera re-ID).
3. **Scale invariance** — the centroid distance threshold scales with bounding box size to handle objects at varying distances from the camera.

---

## 7. Test Coverage

| Test | File | Description |
|------|------|-------------|
| `test_single_detection_creates_track` | `test_tracking.py` | First detection creates new track |
| `test_tracking_persistence` | `test_tracking.py` | Same object tracked across frames |
| `test_track_inactive_after_disappearance` | `test_tracking.py` | Track removed after `max_disappeared` |
| `test_occlusion_same_track_id_retained` | `test_tracking.py` | **Key:** ID preserved through 5-frame gap |
| `test_far_reappearance_creates_new_track` | `test_tracking.py` | Reappearance too far away → new ID |
| `test_direction_estimation` | `test_tracking.py` | Velocity vector accuracy |
| `test_speed_estimation` | `test_tracking.py` | Speed in px/s |

---

*Document maintained by the IBVAP CV Engineering Team — SIH 2026*
