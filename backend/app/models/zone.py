"""Zone model for virtual fence and monitoring regions."""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, JSON, Boolean, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Zone(Base):
    """Virtual fence zone definition for a camera or ad-hoc video analytics.

    Zone types: RESTRICTED, SENSITIVE, PATROL, EXCLUSION, MONITORING
    Geometry supports both 'line' and 'polygon' normalized coordinates.
    """
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cameras.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    zone_type: Mapped[str] = mapped_column(String(30), default="RESTRICTED")
    geometry: Mapped[dict] = mapped_column(JSON, default=dict)
    polygon: Mapped[list] = mapped_column(JSON, default=list)
    direction: Mapped[str] = mapped_column(String(20), default="either",
        comment="'either', 'a_to_b', 'b_to_a'")
    armed_schedule: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    night_only: Mapped[bool] = mapped_column(Boolean, default=False)
    min_confidence: Mapped[float] = mapped_column(Float, default=0.25)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[float] = mapped_column(Float, default=0.5,
        comment="0.0 to 1.0 severity multiplier")
    dwell_threshold_seconds: Mapped[int] = mapped_column(Integer, default=30,
        comment="Seconds before dwell alert triggers")
    color: Mapped[str] = mapped_column(String(20), default="",
        comment="UI color override, e.g. #ff0000")
    description: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

