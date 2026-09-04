"""
API Dependencies — authentication and authorization.

Provides:
- current_user: Extracts and validates the JWT token
- require_permission: Enforces role-based permissions
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.security import decode_access_token, role_has_permission


security = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Extract current user from JWT token.

    Falls back to demo operator when no token is provided.
    """
    if not creds:
        return {"sub": "demo-operator", "role": "OPERATOR"}
    try:
        payload = decode_access_token(creds.credentials)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_permission(permission: str):
    """Dependency factory that enforces a specific permission."""

    def _check(user: dict = Depends(current_user)) -> dict:
        role = user.get("role", "VIEWER")
        if not role_has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' lacks permission '{permission}'",
            )
        return user
    return _check
