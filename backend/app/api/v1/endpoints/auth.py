"""Auth endpoints — login, token refresh, user info."""

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.services.audit import log_action
from backend.app.schemas.common import Token, UserOut
from backend.app.api.deps import current_user

router = APIRouter()


@router.post("/token", response_model=Token)
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate and return a JWT token."""
    u = db.query(User).filter(User.username == username, User.active == True).first()
    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")

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
