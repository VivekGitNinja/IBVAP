"""Camera health model for health time-series tracking."""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Float, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class CameraHealth(Base):
    """Periodic health measurement for a camera.

    Tracks FPS, brightness, blur, frame delta, stream uptime, etc.
    """
    __tablename__ = "camera_health"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), index=True)
    health_score: Mapped[float] = mapped_column(Float, default=100.0)
    status: Mapped[str] = mapped_column(String(20), default="HEALTHY",
        comment="HEALTHY, DEGRADED, OFFLINE")
    fps_actual: Mapped[float] = mapped_column(Float, default=0.0)
    brightness: Mapped[float] = mapped_column(Float, default=128.0)
    blur_score: Mapped[float] = mapped_column(Float, default=0.0)
    frame_delta: Mapped[float] = mapped_column(Float, default=0.0,
        comment="Mean absolute difference from previous frame")
    resolution_width: Mapped[int] = mapped_column(Integer, default=0)
    resolution_height: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    stream_uptime_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    reconnect_count: Mapped[int] = mapped_column(Integer, default=0)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
        index=True)
