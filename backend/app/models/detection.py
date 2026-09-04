"""Detection model for individual AI perception results."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Detection(Base):
    """A single detection result from the perception pipeline.

    Created by the detector adapter (motion, YOLO, ONNX, etc.).
    """
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cameras.id"), nullable=True, index=True)
    job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    media_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    track_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(60), default="unknown")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    bbox_x1: Mapped[int] = mapped_column(Integer, default=0)
    bbox_y1: Mapped[int] = mapped_column(Integer, default=0)
    bbox_x2: Mapped[int] = mapped_column(Integer, default=0)
    bbox_y2: Mapped[int] = mapped_column(Integer, default=0)
    frame_index: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default="motion",
        comment="Detector adapter that produced this detection")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
        index=True)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2)

    @property
    def width(self) -> int:
        return self.bbox_x2 - self.bbox_x1

    @property
    def height(self) -> int:
        return self.bbox_y2 - self.bbox_y1

    @property
    def center(self) -> tuple[int, int]:
        return ((self.bbox_x1 + self.bbox_x2) // 2, (self.bbox_y1 + self.bbox_y2) // 2)
