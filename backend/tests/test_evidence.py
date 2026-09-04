"""Tests for evidence engine — sealing, verification, and hash chain."""

import os
import tempfile
from backend.app.services.evidence import (
    seal_evidence, verify_manifest, verify_evidence_chain,
    compute_file_hash, _sha256,
)


def test_seal_and_verify():
    """Sealing evidence should produce a verifiable manifest."""
    path, digest, manifest = seal_evidence(
        "TEST-001", {"event_id": 1, "score": 85}, camera_id=1
    )
    assert os.path.exists(path)
    assert len(digest) == 64
    assert verify_manifest(path, digest)
    # Cleanup
    os.remove(path)


def test_tampered_manifest_fails():
    """Tampering with manifest should fail verification."""
    path, digest, manifest = seal_evidence(
        "TEST-002", {"event_id": 2, "score": 60}
    )
    assert verify_manifest(path, digest)
    # Tamper
    with open(path, "w") as f:
        f.write("TAMPERED")
    assert not verify_manifest(path, digest)
    # Restore and cleanup
    os.remove(path)


def test_missing_file_fails():
    """Verification of missing file should return False."""
    assert not verify_manifest("/nonexistent/file.json", "abc123")


def test_hash_chain_valid():
    """Valid chain should verify correctly."""
    records = [
        {"sha256": "hash1", "previous_hash": "", "created_at": "2024-01-01T00:00:00"},
        {"sha256": "hash2", "previous_hash": "hash1", "created_at": "2024-01-01T00:01:00"},
        {"sha256": "hash3", "previous_hash": "hash2", "created_at": "2024-01-01T00:02:00"},
    ]
    result = verify_evidence_chain(records)
    assert result["chain_valid"] is True
    assert result["records_count"] == 3


def test_hash_chain_broken():
    """Broken chain should be detected."""
    records = [
        {"sha256": "hash1", "previous_hash": "", "created_at": "2024-01-01T00:00:00"},
        {"sha256": "hash2", "previous_hash": "WRONG_HASH", "created_at": "2024-01-01T00:01:00"},
    ]
    result = verify_evidence_chain(records)
    assert result["chain_valid"] is False
    assert result["broken_at"] is not None


def test_file_hash():
    """compute_file_hash should return SHA-256 of file content."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("test content")
        path = f.name
    try:
        h = compute_file_hash(path)
        assert h is not None
        assert len(h) == 64
        # Verify manually
        import hashlib
        expected = hashlib.sha256(b"test content").hexdigest()
        assert h == expected
    finally:
        os.remove(path)


def test_seal_evidence_includes_metadata():
    """Sealed manifest should include all provided metadata."""
    path, digest, manifest = seal_evidence(
        "TEST-003", {"demo": True}, camera_id=5, camera_name="CAM-05",
        threat_score=78.5
    )
    assert manifest["camera_id"] == 5
    assert manifest["camera_name"] == "CAM-05"
    assert manifest["threat_score"] == 78.5
    assert manifest["version"] == "2.0"
    os.remove(path)
