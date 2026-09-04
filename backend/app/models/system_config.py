"""System configuration model for runtime settings."""

from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class SystemConfig(Base):
    """Runtime system configuration stored in database.

    Allows operators to modify thresholds, modes, and behavior
    without restarting the system.
    """
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="general",
        comment="general, detection, scoring, privacy, demo")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow)
    updated_by: Mapped[str] = mapped_column(String(80), default="system")
