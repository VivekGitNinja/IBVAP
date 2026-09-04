"""PlateRead model for Automatic Number Plate Recognition (ANPR)."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class PlateRead(Base):
    """Stores an extracted license plate observation."""
    __tablename__ = "plate_reads"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    detection_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    camera_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    plate_text: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    frame_index: Mapped[int] = mapped_column(Integer, default=0)
    timestamp_ms: Mapped[float] = mapped_column(Float, default=0.0)
    bbox: Mapped[dict] = mapped_column(JSON, default=dict)
    method: Mapped[str] = mapped_column(String(40), default="ocr")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
