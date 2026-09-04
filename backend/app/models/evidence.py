"""Evidence model for incident evidence with integrity verification."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, DateTime, Float, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Evidence(Base):
    """Evidence record for an incident.

    Includes snapshots, detection metadata, and SHA-256 integrity hashes.
    Supports hash-chain for tamper-evident audit.
    """
    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_incident_type", "incident_id", "evidence_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(30), default="snapshot",
        comment="snapshot, clip, manifest, detection_log")
    file_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    manifest_path: Mapped[str] = mapped_column(String(500))
    manifest_data: Mapped[dict] = mapped_column(JSON, default=dict)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    threat_score: Mapped[float] = mapped_column(Float, default=0.0)
    camera_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    camera_name: Mapped[str] = mapped_column(String(120), default="")
    detection_metadata: Mapped[dict] = mapped_column(JSON, default=dict,
        comment="Detections and track data at time of capture")
    previous_hash: Mapped[str] = mapped_column(String(64), default="",
        comment="Hash of previous evidence record for chain integrity")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
