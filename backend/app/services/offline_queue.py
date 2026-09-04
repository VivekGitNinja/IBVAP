"""
Offline Store-and-Forward Queue Service.

When backend connectivity fails, the edge pipeline writes events locally.
On reconnect, the queue replays events automatically.

Status display:
  OFFLINE MODE — 3 EVENTS QUEUED
  then:
  SYNC RESTORED — 3 EVENTS UPLOADED
"""

from __future__ import annotations
import json
import hashlib
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session

from backend.app.models.sync_queue import SyncQueue


def enqueue_event(
    db: Session,
    event_key: str,
    payload: dict[str, Any],
    event_type: str = "unknown",
    camera_id: int | None = None,
) -> SyncQueue:
    """Add an event to the offline queue.

    Duplicate event_keys are rejected to prevent replay.
    """
    existing = db.query(SyncQueue).filter(SyncQueue.event_key == event_key).first()
    if existing:
        return existing

    entry = SyncQueue(
        event_key=event_key,
        payload=json.dumps(payload),
        payload_json=payload,
        event_type=event_type,
        camera_id=camera_id,
        status="PENDING",
        attempts=0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_pending_count(db: Session) -> int:
    """Count events waiting to be synced."""
    return db.query(SyncQueue).filter(SyncQueue.status == "PENDING").count()


def get_pending_events(db: Session, limit: int = 50) -> list[SyncQueue]:
    """Get pending events for replay."""
    return (
        db.query(SyncQueue)
        .filter(SyncQueue.status == "PENDING")
        .order_by(SyncQueue.created_at)
        .limit(limit)
        .all()
    )


def mark_synced(db: Session, entry_id: int) -> None:
    """Mark an entry as successfully synced."""
    entry = db.get(SyncQueue, entry_id)
    if entry:
        entry.status = "SYNCED"
        db.commit()


def mark_failed(db: Session, entry_id: int, error: str = "") -> None:
    """Mark a sync attempt as failed."""
    entry = db.get(SyncQueue, entry_id)
    if entry:
        entry.attempts += 1
        entry.last_attempt_at = datetime.utcnow()
        entry.error_message = error
        if entry.attempts >= entry.max_attempts:
            entry.status = "FAILED"
        db.commit()


def get_queue_status(db: Session) -> dict[str, Any]:
    """Get current queue status for dashboard display."""
    pending = get_pending_count(db)
    synced = db.query(SyncQueue).filter(SyncQueue.status == "SYNCED").count()
    failed = db.query(SyncQueue).filter(SyncQueue.status == "FAILED").count()
    total = pending + synced + failed

    if pending == 0:
        mode = "ONLINE"
    else:
        mode = "OFFLINE" if failed > 0 else "SYNCING"

    return {
        "mode": mode,
        "pending": pending,
        "synced": synced,
        "failed": failed,
        "total": total,
        "last_updated": datetime.utcnow().isoformat(),
    }


def generate_event_key(event_type: str, camera_id: int, timestamp: datetime) -> str:
    """Generate a deterministic event key for deduplication."""
    raw = f"{event_type}:{camera_id}:{timestamp.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
