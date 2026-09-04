"""
Audit Trail Service.

Records all significant system actions with actor, role, action,
resource, timestamp, and change details.

Audit entries are tamper-evident via hash chaining.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session

from backend.app.models.audit import AuditLog


def _compute_entry_hash(actor: str, action: str, target_type: str,
                         target_id: str, created_at: str,
                         previous_hash: str = "") -> str:
    """Compute tamper-evident hash for an audit entry."""
    raw = f"{actor}:{action}:{target_type}:{target_id}:{created_at}:{previous_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()


def log_action(
    db: Session,
    actor: str,
    actor_role: str,
    action: str,
    target_type: str,
    target_id: str,
    details: dict[str, Any] | None = None,
    ip_address: str = "",
) -> AuditLog:
    """Record an audit trail entry.

    Each entry hashes the previous entry for tamper evidence.
    """
    now = datetime.utcnow()
    now_str = now.isoformat()

    # Get previous hash for chain
    prev = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .first()
    )
    previous_hash = prev.entry_hash if prev else ""

    entry_hash = _compute_entry_hash(
        actor, action, target_type, target_id, now_str, previous_hash
    )

    log = AuditLog(
        actor=actor,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        ip_address=ip_address,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
        created_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def verify_audit_chain(db: Session) -> dict[str, Any]:
    """Verify integrity of the audit log chain."""
    entries = db.query(AuditLog).order_by(AuditLog.id).all()
    chain_valid = True
    broken_at = None

    for i, entry in enumerate(entries):
        if i == 0:
            if entry.previous_hash != "":
                chain_valid = False
                broken_at = entry.id
                break
        else:
            if entry.previous_hash != entries[i - 1].entry_hash:
                chain_valid = False
                broken_at = entry.id
                break

        # Verify the hash itself
        expected = _compute_entry_hash(
            entry.actor, entry.action, entry.target_type, entry.target_id,
            entry.created_at.isoformat(), entry.previous_hash
        )
        if expected != entry.entry_hash:
            chain_valid = False
            broken_at = entry.id
            break

    return {
        "chain_valid": chain_valid,
        "entries_count": len(entries),
        "broken_at": broken_at,
        "verified_at": datetime.utcnow().isoformat(),
    }


def get_audit_trail(
    db: Session,
    target_type: str | None = None,
    target_id: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    """Query audit trail with optional filters."""
    q = db.query(AuditLog)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if target_id:
        q = q.filter(AuditLog.target_id == target_id)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()
