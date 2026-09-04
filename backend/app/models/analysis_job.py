"""AnalysisJob model for asynchronous and real-time video processing."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class AnalysisJob(Base):
    """Tracks background video and stream perception analysis jobs."""

    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), default="upload", index=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    total_frames: Mapped[int] = mapped_column(Integer, default=0)
    processed_frames: Mapped[int] = mapped_column(Integer, default=0)
    detections_count: Mapped[int] = mapped_column(Integer, default=0)
    incidents_count: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    detector_model: Mapped[str] = mapped_column(String(50), default="yolo26")
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.25)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(80), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
