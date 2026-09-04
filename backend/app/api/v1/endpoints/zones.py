"""Zone management endpoints."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.zone import Zone
from backend.app.schemas.common import ZoneIn, ZoneOut
from backend.app.services.audit import log_action
from backend.app.api.deps import current_user

router = APIRouter()


@router.get("", response_model=list[ZoneOut])
def list_zones(camera_id: int | None = None, db: Session = Depends(get_db)):
    """List zones, optionally filtered by camera."""
    q = db.query(Zone)
    if camera_id:
        q = q.filter(Zone.camera_id == camera_id)
    return q.all()


@router.post("", response_model=ZoneOut)
def add_zone(data: ZoneIn, db: Session = Depends(get_db),
             user: dict = Depends(current_user)):
    """Create a new zone."""
    z = Zone(**data.model_dump())
    db.add(z)
    db.commit()
    db.refresh(z)
    log_action(db, user["sub"], user.get("role", ""), "CREATE", "zone",
               str(z.id), {"name": z.name, "zone_type": z.zone_type})
    return z


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    """Get zone details."""
    z = db.get(Zone, zone_id)
    if not z:
        raise HTTPException(404, "Zone not found")
    return z


@router.put("/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, data: ZoneIn, db: Session = Depends(get_db),
                user: dict = Depends(current_user)):
    """Update a zone."""
    z = db.get(Zone, zone_id)
    if not z:
        raise HTTPException(404, "Zone not found")
    for k, v in data.model_dump().items():
        setattr(z, k, v)
    db.commit()
    db.refresh(z)
    log_action(db, user["sub"], user.get("role", ""), "UPDATE", "zone",
               str(z.id), {"name": z.name})
    return z


@router.delete("/{zone_id}")
def delete_zone(zone_id: int, db: Session = Depends(get_db),
                user: dict = Depends(current_user)):
    """Delete a zone."""
    z = db.get(Zone, zone_id)
    if not z:
        raise HTTPException(404, "Zone not found")
    db.delete(z)
    db.commit()
    log_action(db, user["sub"], user.get("role", ""), "DELETE", "zone",
               str(zone_id))
    return {"deleted": True}
