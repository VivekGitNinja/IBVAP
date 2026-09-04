"""Audit log model for tamper-evident operational records."""

from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class AuditLog(Base):
    """Tamper-evident audit log entry.

    Records all significant system actions with actor, role, action,
    resource, timestamp, and change details.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor", "created_at"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    actor_role: Mapped[str] = mapped_column(String(30), default="")
    action: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    entry_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
        index=True)
