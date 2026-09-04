"""Test configuration — creates test database and tables."""

import os
import pytest

# Use a separate SQLite DB for tests
os.environ["DATABASE_URL"] = "sqlite:///./test_ibvap.db"

from backend.app.db.session import engine, SessionLocal
from backend.app.db.base import Base  # noqa: E402 — imports all models


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    """Create all tables and seed default cameras/users once for the test session."""
    Base.metadata.create_all(bind=engine)

    from backend.app.models.user import User
    from backend.app.models.camera import Camera
    from backend.app.core.security import hash_password

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "operator").first():
            db.add(User(
                username="operator",
                password_hash=hash_password("operator123"),
                role="OPERATOR",
                full_name="Default Operator",
            ))
            db.add(User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="ADMIN",
                full_name="System Admin",
            ))
            db.add(User(
                username="commander",
                password_hash=hash_password("commander123"),
                role="COMMANDER",
                full_name="Border Commander",
            ))

        if db.query(Camera).count() == 0:
            db.add(Camera(
                name="BOP-01 Gate Camera",
                stream_url="demo://synthetic",
                location="Demo Border Sector Alpha",
                bop="BOP-01",
                status="ONLINE",
                health_score=98,
                latitude=28.6139,
                longitude=77.2090,
                fps=10,
                resolution="1280x720",
            ))
            db.add(Camera(
                name="BOP-01 Perimeter Cam",
                stream_url="demo://synthetic",
                location="Demo Border Sector Alpha",
                bop="BOP-01",
                status="ONLINE",
                health_score=95,
                latitude=28.6145,
                longitude=77.2100,
                fps=10,
                resolution="1280x720",
            ))
        db.commit()
    finally:
        db.close()

    yield
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        os.remove("./test_ibvap.db")
    except OSError:
        pass
