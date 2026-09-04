"""Watchlist model for facial recognition target matching."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class Watchlist(Base):
    """Enrolled subjects for facial recognition candidate matching."""
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    face_image_path: Mapped[str] = mapped_column(String(500), default="")
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
