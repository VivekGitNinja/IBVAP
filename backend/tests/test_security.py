"""Security test suite — authentication, authorization, RBAC, CORS, rate limiting, and path traversal."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    role_has_permission,
)

client = TestClient(app)


def test_password_hashing():
    """Verify PBKDF2 password hashing and verification."""
    h = hash_password("secret_pass")
    assert verify_password("secret_pass", h)
    assert not verify_password("wrong_pass", h)


def test_jwt_token_lifecycle():
    """Verify JWT token encoding and decoding."""
    token = create_access_token("operator", "OPERATOR")
    p = decode_access_token(token)
    assert p["sub"] == "operator"
    assert p["role"] == "OPERATOR"


def test_unauthenticated_request_blocked():
    """Endpoints protected by current_user must reject unauthenticated requests with 401."""
    # Try acknowledging an incident without token
    r = client.post("/api/v1/incidents/1/acknowledge")
    assert r.status_code == 401
    assert "detail" in r.json()

    # Try listing evidence without token
    r = client.get("/api/v1/evidence/1")
    assert r.status_code == 401


def test_invalid_token_rejected():
    """Tampered or invalid JWT must return 401."""
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    r = client.post("/api/v1/incidents/1/acknowledge", headers=headers)
    assert r.status_code == 401


def test_rbac_permission_matrix():
    """Verify RBAC role permission matrix boundaries."""
    assert role_has_permission("ADMIN", "manage_users")
    assert role_has_permission("ADMIN", "manage_cameras")
    assert role_has_permission("COMMANDER", "manage_cameras")
    assert not role_has_permission("COMMANDER", "manage_users")
    assert role_has_permission("OPERATOR", "acknowledge_incidents")
    assert not role_has_permission("OPERATOR", "manage_users")
    assert role_has_permission("VIEWER", "read")
    assert not role_has_permission("VIEWER", "write")
    assert not role_has_permission("VIEWER", "acknowledge_incidents")


def test_rate_limiting_lockout_on_auth():
    """Verify brute-force rate limiting returns HTTP 429 after threshold."""
    # Attempt rapid failed logins
    for _ in range(5):
        client.post("/api/v1/auth/token", data={"username": "attacker", "password": "wrongpassword"})

    # 6th attempt must trigger HTTP 429
    r = client.post("/api/v1/auth/token", data={"username": "attacker", "password": "wrongpassword"})
    assert r.status_code == 429
    assert "locked" in r.json()["detail"].lower()


def test_evidence_clip_path_traversal_blocked():
    """Path traversal attempt in filename must be prevented."""
    token = create_access_token("operator", "OPERATOR")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/evidence/clip/1/../../../../etc/passwd", headers=headers)
    # Must return 404 (file not found), not leak host filesystem
    assert r.status_code == 404

