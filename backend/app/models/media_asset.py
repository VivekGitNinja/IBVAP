"""MediaAsset model for uploaded video files."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class MediaAsset(Base):
    """Represents an uploaded video or media asset for real computer vision analysis."""

    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), index=True)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100), default="video/mp4")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    total_frames: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="READY", index=True)
    uploaded_by: Mapped[str] = mapped_column(String(80), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
