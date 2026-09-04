"""
Unit and integration tests for ONVIF PTZ Controls and Circular Buffer NVR Video Clips.
"""

import os
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.live_pipeline import CameraPipeline


client = TestClient(app)


def test_ptz_commands():
    """Verify PTZ direction and zoom adjustments update the camera state."""
    # Pan left
    resp = client.post("/api/v1/cameras/1/ptz", json={"direction": "left", "speed": 0.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["ptz_state"]["pan"] < 0

    # Tilt up
    resp = client.post("/api/v1/cameras/1/ptz", json={"direction": "up", "speed": 0.5})
    assert resp.status_code == 200
    assert resp.json()["ptz_state"]["tilt"] > 0

    # Zoom in
    resp = client.post("/api/v1/cameras/1/ptz", json={"direction": "zoom_in", "speed": 0.5})
    assert resp.status_code == 200
    assert resp.json()["ptz_state"]["zoom"] > 1.0

    # Home reset
    resp = client.post("/api/v1/cameras/1/ptz", json={"direction": "home"})
    assert resp.status_code == 200
    state = resp.json()["ptz_state"]
    assert state["pan"] == 0.0
    assert state["tilt"] == 0.0
    assert state["zoom"] == 1.0
    assert state["preset"] == "HOME"


def test_ptz_presets():
    """Verify PTZ preset listing and navigation."""
    resp = client.get("/api/v1/cameras/1/ptz/presets")
    assert resp.status_code == 200
    presets = resp.json()["presets"]
    assert len(presets) >= 4
    preset_ids = [p["id"] for p in presets]
    assert "WATCHTOWER" in preset_ids
    assert "HOME" in preset_ids

    # Navigate to WATCHTOWER preset
    resp = client.post("/api/v1/cameras/1/ptz/goto", json={"preset": "WATCHTOWER"})
    assert resp.status_code == 200
    state = resp.json()["ptz_state"]
    assert state["preset"] == "WATCHTOWER"
    assert state["pan"] == 45.0
    assert state["tilt"] == 10.0
    assert state["zoom"] == 2.2


def test_nvr_clip_generation():
    """Verify circular ring buffer synthesizes a valid signed MP4/AVI clip."""
    pipeline = CameraPipeline(camera_id=1, stream_url="demo://bop1", camera_name="Test Cam", bop="BOP-01")
    
    # Fill ring buffer with synthetic frames
    for i in range(20):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:] = (i * 10, 50, 100)
        pipeline._frame_ring_buffer.append(frame)

    assert len(pipeline._frame_ring_buffer) == 20

    clip_url, clip_hash, file_size, file_path = pipeline._generate_nvr_clip("TEST-NVR-99")
    
    assert clip_url is not None
    assert "/api/v1/evidence/clips/" in clip_url
    assert clip_hash is not None and len(clip_hash) == 64
    assert file_size > 0
    assert os.path.exists(file_path)


from backend.app.core.security import create_access_token


def test_websocket_stream_handshake():
    """Verify WebSocket live video stream connects and delivers frames with valid auth."""
    token = create_access_token("operator", "OPERATOR")
    with client.websocket_connect(f"/ws/live/1?token={token}") as ws:
        frame_bytes = ws.receive_bytes()
        assert len(frame_bytes) > 500
        # Check JPEG SOI (0xFF, 0xD8) magic bytes
        assert frame_bytes[:2] == b"\xff\xd8"


def test_websocket_stream_unauthenticated():
    """Verify WebSocket live video stream rejects unauthenticated connection."""
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/live/1"):
            pass
