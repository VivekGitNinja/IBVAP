"""User model with role-based access control."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base


class User(Base):
    """System user with role-based permissions.

    Roles: ADMIN, COMMANDER, OPERATOR, AUDITOR, VIEWER
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="OPERATOR")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
