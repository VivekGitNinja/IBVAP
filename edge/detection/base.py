"""Detection data types for the perception pipeline."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Tuple


@dataclass
class Detection:
    """A single detection result from a detector adapter."""
    label: str = "unknown"
    confidence: float = 0.0
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (x1, y1, x2, y2)
    class_id: int = 0
    class_name: str = "unknown"
    frame_id: int = 0
    center: list = None
    source: str = "fallback"
    track_id: str | None = None

    def __post_init__(self):
        if self.center is None:
            x1, y1, x2, y2 = self.bbox
            self.center = [(x1 + x2) / 2, (y1 + y2) / 2]

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]


class Detector(Protocol):
    """Protocol for detector adapters."""
    def detect(self, frame) -> list[Detection]: ...
