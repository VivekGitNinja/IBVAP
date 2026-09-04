"""Track model for persistent object tracking across frames."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, JSON, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Track(Base):
    """A tracked object across multiple frames.

    Maintains trajectory, dwell time, direction, and zone membership.
    """
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), index=True)
    track_id: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(60), default="unknown")
    confidence_avg: Mapped[float] = mapped_column(Float, default=0.0)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    trajectory: Mapped[list] = mapped_column(JSON, default=list,
        comment="List of [x, y, timestamp] points")
    dwell_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    total_distance: Mapped[float] = mapped_column(Float, default=0.0,
        comment="Estimated total distance in pixels")
    speed_estimate: Mapped[float] = mapped_column(Float, default=0.0,
        comment="Average speed in pixels/sec")
    direction: Mapped[str] = mapped_column(String(30), default="unknown",
        comment="Primary movement direction")
    zone_ids: Mapped[list] = mapped_column(JSON, default=list,
        comment="List of zone IDs the track has entered")
    current_zone_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frame_count: Mapped[int] = mapped_column(Integer, default=0)
    last_bbox: Mapped[dict] = mapped_column(JSON, default=dict,
        comment="Last known bbox {x1,y1,x2,y2}")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
