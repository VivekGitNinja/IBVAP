"""Zone model for virtual fence and monitoring regions."""

from datetime import datetime
from sqlalchemy import String, JSON, Boolean, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Zone(Base):
    """Polygon zone definition for a camera.

    Zone types: RESTRICTED, SENSITIVE, PATROL, EXCLUSION, MONITORING
    Colors are configurable UI themes.
    """
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    zone_type: Mapped[str] = mapped_column(String(30), default="RESTRICTED")
    polygon: Mapped[list] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[float] = mapped_column(Float, default=0.5,
        comment="0.0 to 1.0 severity multiplier")
    dwell_threshold_seconds: Mapped[int] = mapped_column(Integer, default=30,
        comment="Seconds before dwell alert triggers")
    color: Mapped[str] = mapped_column(String(20), default="",
        comment="UI color override, e.g. #ff0000")
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
