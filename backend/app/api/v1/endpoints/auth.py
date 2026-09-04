import time
from collections import defaultdict
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.services.audit import log_action
from backend.app.schemas.common import Token, UserOut
from backend.app.api.deps import current_user

router = APIRouter()

# Rate limiting for auth brute-force prevention
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_WINDOW = 60.0  # seconds


def _check_rate_limit(key: str):
    now = time.time()
    attempts = [t for t in _failed_attempts[key] if now - t < _LOCKOUT_WINDOW]
    _failed_attempts[key] = attempts
    if len(attempts) >= _MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many failed authentication attempts. Account locked for 60 seconds.",
        )


def _record_failed_attempt(key: str):
    _failed_attempts[key].append(time.time())


def _reset_attempts(key: str):
    _failed_attempts.pop(key, None)


@router.post("/token", response_model=Token)
@router.post("/login", response_model=Token)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate and return a JWT token with brute-force rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{username}"
    _check_rate_limit(rate_key)

    u = db.query(User).filter(User.username == username, User.active == True).first()
    if not u or not verify_password(password, u.password_hash):
        _record_failed_attempt(rate_key)
        raise HTTPException(401, "Invalid credentials")

    _reset_attempts(rate_key)
    u.last_login = datetime.utcnow()
    db.commit()

    log_action(db, u.username, u.role, "LOGIN", "user", str(u.id))

    return {"access_token": create_access_token(u.username, u.role), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_current_user(user: dict = Depends(current_user)):
    """Get current authenticated user info."""
    return {
        "id": 0,
        "username": user["sub"],
        "role": user["role"],
        "full_name": "",
        "active": True,
    }
