"""Evidence management and verification endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.evidence import Evidence
from backend.app.services.evidence import verify_manifest, verify_evidence_chain
from backend.app.services.audit import log_action
from backend.app.schemas.common import EvidenceOut, EvidenceVerification
from backend.app.api.deps import current_user

router = APIRouter()


@router.get("/{incident_id}", response_model=list[EvidenceOut])
def list_evidence(incident_id: int, db: Session = Depends(get_db)):
    """Get all evidence for an incident."""
    return (
        db.query(Evidence)
        .filter(Evidence.incident_id == incident_id)
        .order_by(Evidence.created_at)
        .all()
    )


@router.get("/verify/{evidence_id}")
def verify_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Verify integrity of an evidence record."""
    e = db.get(Evidence, evidence_id)
    if not e:
        raise HTTPException(404, "Evidence not found")

    valid = verify_manifest(e.manifest_path, e.sha256)

    log_action(db, "system", "", "VERIFY", "evidence", str(evidence_id),
               {"valid": valid})

    return {
        "valid": valid,
        "sha256": e.sha256,
        "manifest_path": e.manifest_path,
        "verified_at": datetime.utcnow().isoformat(),
    }


@router.get("/chain/{incident_id}")
def verify_evidence_chain_endpoint(incident_id: int,
                                    db: Session = Depends(get_db)):
    """Verify hash-chain integrity of all evidence for an incident."""
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
def get_section_65b_certificate(evidence_id: int, db: Session = Depends(get_db)):
    """Generate Section 65B Indian Evidence Act Court-Admissibility Certificate."""
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

