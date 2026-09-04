"""Alert model for operator notifications."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Alert(Base):
    """Operator alert linked to an incident.

    Priority is derived from the incident threat score.
    """
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="NEW")
    message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
