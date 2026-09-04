"""
Pytest suite for GET /api/v1/analysis/jobs/{job_id}/tracks endpoint.
Tests multi-object track summary generation, normalized centroid paths,
speed calculation, zone correlation, and 404 handling.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.analysis_job import AnalysisJob
from backend.app.models.detection import Detection
from backend.app.models.incident import Incident
from backend.app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token("admin", "ADMIN")
    return {"Authorization": f"Bearer {token}"}


def test_tracks_endpoint_not_found(client, auth_headers):
    """Assert 404 for non-existent analysis job."""
    resp = client.get("/api/v1/analysis/jobs/999999/tracks", headers=auth_headers)
    assert resp.status_code == 404
    assert "Analysis job not found" in resp.json()["detail"]


def test_tracks_endpoint_empty_job(client, auth_headers):
    """Assert empty track list for job with no detections."""
    db = SessionLocal()
    try:
        job = AnalysisJob(
            source_type="upload",
            source_id=None,
            source_url="test_empty.mp4",
            status="completed",
            detector_model="motion",
            total_frames=10,
            processed_frames=10,
        )
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    resp = client.get(f"/api/v1/analysis/jobs/{job_id}/tracks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["tracks"] == []
    assert data["total_tracks"] == 0


def test_tracks_endpoint_with_real_detections_and_incident(client, auth_headers):
    """Assert full track summary with normalized path, speed, and incident zone correlation."""
    db = SessionLocal()
    try:
        job = AnalysisJob(
            source_type="upload",
            source_id=None,
            source_url="test_fixture.mp4",
            status="completed",
            fps=25.0,
            total_frames=50,
            processed_frames=50,
        )
        db.add(job)
        db.commit()
        job_id = job.id

        # Add detections for Track T-1 (person moving across frame)
        for i in range(5):
            det = Detection(
                job_id=job_id,
                track_id="TRK-1",
                label="person",
                confidence=0.92,
                bbox_x1=100 + i * 20,
                bbox_y1=150 + i * 10,
                bbox_x2=160 + i * 20,
                bbox_y2=250 + i * 10,
                frame_index=i * 5,
                source="yolo26",
                payload={"timestamp_ms": i * 200.0, "night": i >= 3},
            )
            db.add(det)

        # Add detections for Track T-2 (vehicle)
        for i in range(3):
            det = Detection(
                job_id=job_id,
                track_id="TRK-2",
                label="car",
                confidence=0.88,
                bbox_x1=400 + i * 50,
                bbox_y1=300,
                bbox_x2=550 + i * 50,
                bbox_y2=400,
                frame_index=i * 10,
                source="yolo26",
                payload={"timestamp_ms": i * 400.0, "night": False},
            )
            db.add(det)

        # Add Incident linked to TRK-1 in zone "Perimeter North"
        inc = Incident(
            incident_code=f"INC-TEST-TRK1-{job_id}",
            title="Perimeter Breach",
            severity="HIGH",
            threat_score=85.0,
            zone_name="Perimeter North",
            track_ids=["TRK-1"],
            job_id=job_id,
        )
        db.add(inc)

        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/v1/analysis/jobs/{job_id}/tracks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["total_tracks"] == 2

    tracks = {t["track_id"]: t for t in data["tracks"]}
    assert "TRK-1" in tracks
    assert "TRK-2" in tracks

    t1 = tracks["TRK-1"]
    assert t1["class"] == "person"
    assert t1["first_frame"] == 0
    assert t1["last_frame"] == 20
    assert t1["detections_count"] == 5
    assert len(t1["path"]) == 5
    # Normalized coords must be in [0.0, 1.0]
    for pt in t1["path"]:
        assert 0.0 <= pt[0] <= 1.0
        assert 0.0 <= pt[1] <= 1.0
        assert isinstance(pt[2], int)
    # Zone North touched
    assert "Perimeter North" in t1["zones_touched"]
    # Night frame percentage: 2 out of 5 frames (40.0%)
    assert t1["night_frame_pct"] == 40.0
    assert t1["max_speed"] > 0.0

    t2 = tracks["TRK-2"]
    assert t2["class"] == "car"
    assert t2["first_frame"] == 0
    assert t2["last_frame"] == 20
    assert t2["detections_count"] == 3
    assert t2["night_frame_pct"] == 0.0
