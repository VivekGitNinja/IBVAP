"""Camera model for CCTV management."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Camera(Base):
    """Represents a CCTV camera or video source.

    Supports RTSP, ONVIF, uploaded video, webcam, and demo sources.
    """
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    stream_url: Mapped[str] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(200), default="Unknown")
    bop: Mapped[str] = mapped_column(String(120), default="BOP-01")
    camera_type: Mapped[str] = mapped_column(String(40), default="IP")
    fps: Mapped[int] = mapped_column(Integer, default=10)
    resolution: Mapped[str] = mapped_column(String(30), default="1280x720")
    status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    health_score: Mapped[float] = mapped_column(Float, default=0)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    detection_interval: Mapped[int] = mapped_column(Integer, default=3,
        comment="Process every Nth frame")
    max_inference_fps: Mapped[int] = mapped_column(Integer, default=5)
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow)
