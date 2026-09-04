"""Incident model for prioritized security incidents."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Incident(Base):
    """A prioritized security incident requiring human verification.

    Contains explainable AI assessment with reasons, confidence,
    supporting signals, and recommended actions.
    """
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="LOW")
    threat_score: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0,
        comment="AI confidence in the assessment")
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    event_ids: Mapped[list] = mapped_column(JSON, default=list)
    detection_ids: Mapped[list] = mapped_column(JSON, default=list)
    track_ids: Mapped[list] = mapped_column(JSON, default=list)
    camera_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    camera_name: Mapped[str] = mapped_column(String(120), default="")
    zone_name: Mapped[str] = mapped_column(String(100), default="")
    fingerprint: Mapped[str] = mapped_column(String(128), default="",
        comment="Deduplication fingerprint")
    correlated_ids: Mapped[list] = mapped_column(JSON, default=list,
        comment="Related incident IDs from multi-camera correlation")
    recommended_action: Mapped[str] = mapped_column(String(300),
        default="Verify incident on live feed.")
    ai_assessment: Mapped[dict] = mapped_column(JSON, default=dict,
        comment="Structured AI explanation payload")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
        index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escalated_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    timeline: Mapped[list] = mapped_column(JSON, default=list,
        comment="Ordered list of timeline events")
