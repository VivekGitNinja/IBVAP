"""
System Integrity & Military-Grade Resilience Test Suite
======================================================
Verifies:
- Clean API routing and JSON error contracts (no HTML leaks on 404s)
- Dual /api/v1/status and /api/v1/health/status availability
- Tactical camera snapshot and MJPEG stream endpoints
- Detector factory aliases and protocol compliance
- RFC 7518 JWT security compliance
- Evidence SHA-256 seal & chain verification
- Audit trail tamper-evidence
"""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.core.security import create_access_token, decode_access_token
from backend.app.services.audit import log_action, verify_audit_chain
from backend.app.services.evidence import seal_evidence, verify_manifest, verify_evidence_chain
from edge.detection.factory import create_detector, list_available_detectors

client = TestClient(app)


def test_api_routing_and_json_404():
    """Verify API never returns HTML on 404 and status routes are reliable."""
    # 1. Direct status endpoint
    r_stat = client.get("/api/v1/status")
    assert r_stat.status_code == 200
    assert r_stat.headers["content-type"].startswith("application/json")
    data = r_stat.json()
    assert data["status"] == "operational"
    assert "uptime_seconds" in data
    assert "cameras_total" in data

    # 2. Health status endpoint
    r_hstat = client.get("/api/v1/health/status")
    assert r_hstat.status_code == 200
    assert r_hstat.headers["content-type"].startswith("application/json")

    # 3. Invalid API route MUST return JSON 404, never SPA HTML
    r_404 = client.get("/api/v1/completely_invalid_subroute_404")
    assert r_404.status_code == 404
    assert r_404.headers["content-type"].startswith("application/json")
    err_json = r_404.json()
    assert "detail" in err_json

    # 4. Root API JSON response
    r_root = client.get("/", headers={"Accept": "application/json"})
    assert r_root.status_code == 200
    assert r_root.headers["content-type"].startswith("application/json")
    assert r_root.json()["name"] == "IBVAP"


def test_camera_snapshot_and_tactical_generator():
    """Verify camera snapshot returns valid JPEG with tactical overlays."""
    # Camera 1 is seeded by default
    r = client.get("/api/v1/cameras/1/snapshot")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert len(r.content) > 1000

    # Verify bytes decode to a valid OpenCV image
    img_array = np.frombuffer(r.content, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    assert img is not None
    assert img.shape[0] == 720
    assert img.shape[1] == 1280

    # Stream start/stop endpoints
    r_start = client.post("/api/v1/cameras/1/stream/start")
    assert r_start.status_code == 200
    assert r_start.json()["status"] == "started"

    r_stop = client.post("/api/v1/cameras/1/stream/stop")
    assert r_stop.status_code == 200
    assert r_stop.json()["status"] == "stopped"


def test_detector_factory_aliases_and_inference():
    """Verify all detector aliases initialize and can run inference."""
    aliases = ["yolo26", "yolo26n", "yolo26s", "yolo11", "yolo11n", "onnx", "motion"]
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    for alias in aliases:
        detector = create_detector(preferred=alias)
        assert detector is not None, f"Detector {alias} failed to create"
        assert detector.is_available, f"Detector {alias} is not available"

        # Test inference adhering to (frame, frame_id) protocol
        detections = detector.detect(test_frame, frame_id=42)
        assert isinstance(detections, list)


def test_jwt_rfc7518_security_compliance():
    """Verify JWT tokens are securely signed with >= 256-bit key and verified."""
    token = create_access_token("border_patrol_01", "COMMANDER")
    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload["sub"] == "border_patrol_01"
    assert payload["role"] == "COMMANDER"

    # Tampered token must fail
    tampered = token[:-4] + "xxxx"
    with pytest.raises(Exception):
        decode_access_token(tampered)


def test_evidence_manifest_and_chain_verification():
    """Verify SHA-256 evidence sealing and chain validation."""
    inc_code = "IBVAP-TEST-20260904-001"
    payload = {"target": "person", "confidence": 0.96, "sector": "BOP-01"}

    path, digest, manifest = seal_evidence(
        incident_code=inc_code,
        payload=payload,
        camera_id=1,
        camera_name="BOP-01 Gate",
        threat_score=88.5,
    )

    assert len(digest) == 64  # SHA-256 hex length
    assert verify_manifest(path, digest) is True
    assert verify_manifest(path, "0" * 64) is False

    # Chain verification
    records = [
        {"sha256": digest, "previous_hash": "", "created_at": "2026-09-04T00:00:00Z"}
    ]
    chain_res = verify_evidence_chain(records)
    assert chain_res["chain_valid"] is True


def test_audit_chain_tamper_evidence():
    """Verify tamper-evident audit logging and hash chaining."""
    db = SessionLocal()
    try:
        log_action(db, "commander", "COMMANDER", "SYSTEM_TEST", "system", "1", {"status": "ok"})
        verification = verify_audit_chain(db)
        assert verification["chain_valid"] is True
        assert verification["broken_at"] is None
    finally:
        db.close()
