"""Object tracking module.

Provides:
- CentroidTracker: simple centroid-based tracker
- ByteTracker: Kalman + IoU tracker (ByteTrack-inspired)
"""

from edge.tracking.centroid import CentroidTracker, TrackedObject
from edge.tracking.bytetrack import ByteTracker

__all__ = ["CentroidTracker", "TrackedObject", "ByteTracker"]
