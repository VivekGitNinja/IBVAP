"""
Security module — authentication, authorization, and password hashing.

Uses PBKDF2-HMAC-SHA256 for password hashing (Python 3.9 compatible).
Roles: ADMIN, COMMANDER, OPERATOR, AUDITOR, VIEWER
"""

from __future__ import annotations
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from backend.app.core.config import settings


# ── Password Hashing ──────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return f"pbkdf2$100000${salt.hex()}${dk.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against its hash."""
    try:
        parts = encoded.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2":
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            dk_hex = parts[3]
            dk_len = len(bytes.fromhex(dk_hex))
            calc = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, iterations, dklen=dk_len
            )
            return hmac.compare_digest(calc, bytes.fromhex(dk_hex))
        # Legacy scrypt format
        _, n, r, p, salt_hex, dk_hex = parts
        salt = bytes.fromhex(salt_hex)
        dk_len = len(bytes.fromhex(dk_hex))
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=dk_len)
        return hmac.compare_digest(calc, bytes.fromhex(dk_hex))
    except Exception:
        return False


# ── JWT Tokens ────────────────────────────────────────────────

def create_access_token(subject: str, role: str) -> str:
    """Create a JWT access token."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": subject, "role": role, "exp": exp, "iat": datetime.now(timezone.utc)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


# ── Role-Based Access Control ─────────────────────────────────

ROLE_HIERARCHY = {
    "ADMIN": 5,
    "COMMANDER": 4,
    "OPERATOR": 3,
    "AUDITOR": 2,
    "VIEWER": 1,
}

ROLE_PERMISSIONS = {
    "ADMIN": {"read", "write", "delete", "manage_users", "manage_cameras",
              "manage_zones", "manage_config", "view_audit", "export_evidence",
              "acknowledge_incidents", "escalate_incidents", "run_demo"},
    "COMMANDER": {"read", "write", "manage_cameras", "manage_zones",
                  "view_audit", "acknowledge_incidents", "escalate_incidents",
                  "run_demo"},
    "OPERATOR": {"read", "write", "acknowledge_incidents", "run_demo"},
    "AUDITOR": {"read", "view_audit", "export_evidence"},
    "VIEWER": {"read"},
}


def role_has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms


def role_level(role: str) -> int:
    """Get numeric level for a role."""
    return ROLE_HIERARCHY.get(role, 0)
