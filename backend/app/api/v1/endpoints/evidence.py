"""Evidence management and verification endpoints."""

from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.evidence import Evidence
from backend.app.services.evidence import verify_manifest, verify_evidence_chain
from backend.app.services.audit import log_action
from backend.app.schemas.common import EvidenceOut, EvidenceVerification
from backend.app.api.deps import current_user

router = APIRouter()


@router.get("/{incident_id}", response_model=list[EvidenceOut])
def list_evidence(
    incident_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Get all evidence for an incident (authenticated)."""
    return (
        db.query(Evidence)
        .filter(Evidence.incident_id == incident_id)
        .order_by(Evidence.created_at)
        .all()
    )


@router.get("/{evidence_id}/verify")
@router.get("/verify/{evidence_id}")
def verify_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Verify integrity of an evidence record against disk file hash (authenticated)."""
    import os
    from backend.app.services.evidence import compute_file_hash

    e = db.get(Evidence, evidence_id)
    if not e:
        raise HTTPException(404, "Evidence not found")

    computed = None
    if e.file_path and os.path.exists(e.file_path):
        computed = compute_file_hash(e.file_path)
    elif e.manifest_path and os.path.exists(e.manifest_path):
        computed = compute_file_hash(e.manifest_path)

    match = bool(computed and e.sha256 and (computed.lower() == e.sha256.lower()))

    log_action(
        db,
        user.get("sub", "system"),
        user.get("role", "OPERATOR"),
        "VERIFY",
        "evidence",
        str(evidence_id),
        {"match": match, "sha256": e.sha256, "computed": computed},
    )

    return {
        "match": match,
        "valid": match,
        "evidence_id": evidence_id,
        "stored_hash": e.sha256,
        "computed_hash": computed,
        "manifest_path": e.manifest_path,
        "file_path": e.file_path,
        "statutory_compliance": "Bharatiya Sakshya Adhiniyam, 2023 §63",
        "verified_at": datetime.utcnow().isoformat(),
    }


@router.get("/chain/{incident_id}")
def verify_evidence_chain_endpoint(
    incident_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Verify hash-chain integrity of all evidence for an incident (authenticated)."""
    evidence = (
        db.query(Evidence)
        .filter(Evidence.incident_id == incident_id)
        .order_by(Evidence.created_at)
        .all()
    )
    records = [
        {
            "sha256": e.sha256,
            "previous_hash": getattr(e, "previous_hash", ""),
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in evidence
    ]
    return verify_evidence_chain(records)


@router.get("/certificate/{evidence_id}")
def get_section_65b_certificate(
    evidence_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Generate Section 65B Indian Evidence Act Court-Admissibility Certificate (authenticated)."""
    from backend.app.services.evidence import generate_section_65b_certificate
    from backend.app.models.incident import Incident

    e = db.get(Evidence, evidence_id)
    if not e:
        raise HTTPException(404, "Evidence not found")

    inc = db.get(Incident, e.incident_id) if e.incident_id else None
    inc_code = inc.incident_code if inc else f"INC-{e.incident_id}"

    cert = generate_section_65b_certificate(
        evidence_id=e.id,
        incident_code=inc_code,
        sha256_digest=e.sha256,
        camera_name=e.camera_name or "BOP Surveillance Node",
    )
    return cert


@router.get("/clip/{incident_id}/{filename}")
def get_evidence_clip(
    incident_id: int,
    filename: str,
    user: dict = Depends(current_user),
):
    """Securely stream or download an evidence video clip with strict authentication and traversal guard."""
    safe_filename = Path(filename).name
    clip_dir = Path(settings.evidence_dir) / "clips"
    clip_path = clip_dir / f"incident_{incident_id}" / safe_filename
    if not clip_path.is_file():
        clip_path = clip_dir / safe_filename
        if not clip_path.is_file():
            raise HTTPException(404, "Evidence video clip not found")
    return FileResponse(clip_path, media_type="video/mp4")


