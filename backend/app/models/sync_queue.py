"""Sync queue model for offline store-and-forward."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class SyncQueue(Base):
    """Offline event queue for store-and-forward.

    When the backend is unreachable, events are written locally.
    On reconnect, the queue replays events automatically.
    """
    __tablename__ = "sync_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    payload: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    event_type: Mapped[str] = mapped_column(String(50), default="unknown")
    camera_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
