"""
IBVAP — Intelligent Border Video Analytics Platform
FastAPI Application Entry Point
"""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.db.session import engine, SessionLocal
from backend.app.db.base import Base
from backend.app.api.v1.router import api
from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.models.camera import Camera
from backend.app.core.security import hash_password
from backend.app.services.live_pipeline import live_manager

# Startup time for uptime calculation
_startup_time = time.time()

# Active WebSocket connections for real-time events
_active_connections: list[WebSocket] = []
# Reference to the running event loop, set during startup
_event_loop = None


def get_uptime() -> float:
    return time.time() - _startup_time


def get_ws_connections() -> list[WebSocket]:
    return _active_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle.

    IMPORTANT: Only ONE yield. Everything before yield = startup.
    Everything after yield = shutdown.
    """
    global _event_loop
    _event_loop = asyncio.get_event_loop()

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Bootstrap default data
    db = SessionLocal()
    try:
        # Create default operator user
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
            db.commit()

        # Create demo cameras if none exist
        if db.query(Camera).count() == 0:
            demo_cameras = [
                Camera(
                    name="BOP-01 Gate Camera", stream_url="demo://synthetic",
                    location="Demo Border Sector Alpha", bop="BOP-01",
                    status="ONLINE", health_score=98, latitude=28.6139,
                    longitude=77.2090, fps=10, resolution="1280x720",
                ),
                Camera(
                    name="BOP-01 Perimeter Cam", stream_url="demo://synthetic",
                    location="Demo Border Sector Alpha", bop="BOP-01",
                    status="ONLINE", health_score=95, latitude=28.6145,
                    longitude=77.2100, fps=10, resolution="1280x720",
                ),
                Camera(
                    name="BOP-02 Watchtower Cam", stream_url="demo://synthetic",
                    location="Demo Border Sector Beta", bop="BOP-02",
                    status="ONLINE", health_score=92, latitude=28.6200,
                    longitude=77.2150, fps=15, resolution="1920x1080",
                ),
                Camera(
                    name="BOP-03 Road Checkpoint", stream_url="demo://synthetic",
                    location="Demo Border Sector Gamma", bop="BOP-03",
                    status="DEGRADED", health_score=62, latitude=28.6250,
                    longitude=77.2200, fps=8, resolution="1280x720",
                ),
                Camera(
                    name="BOP-04 Night Patrol", stream_url="demo://synthetic",
                    location="Demo Border Sector Delta", bop="BOP-04",
                    status="OFFLINE", health_score=0, latitude=28.6300,
                    longitude=77.2250, fps=10, resolution="640x480",
                ),
            ]
            for cam in demo_cameras:
                db.add(cam)
            db.commit()

        # ── Wire live pipeline events → WebSocket broadcast (STARTUP) ──
        def on_live_event(event):
            if _event_loop and _event_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    broadcast_event(event["type"], event),
                    _event_loop,
                )
        live_manager.add_event_listener(on_live_event)

        # ── Start live pipelines for persistent RTSP streams (STARTUP) ──
        # Exclude host USB webcams so user camera does not turn on automatically at boot
        try:
            cameras = db.query(Camera).filter(
                Camera.stream_url.notlike("demo://%"),
                Camera.stream_url.notlike("usb://%"),
                Camera.stream_url.notlike(""),
                Camera.active == True,
            ).all()
            for cam in cameras:
                live_manager.start_camera(
                    camera_id=cam.id,
                    stream_url=cam.stream_url,
                    camera_name=cam.name,
                    bop=cam.bop,
                )
        except Exception as e:
            print(f"Pipeline startup warning: {e}")
    finally:
        db.close()

    # ══════ SINGLE YIELD — everything above runs at startup ══════
    yield
    # ══════ everything below runs at shutdown ══════

    # Cleanup
    live_manager.stop_all()
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Edge-first border video incident intelligence platform — SIH 2026",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8001", "http://127.0.0.1:8001"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# Request timing middleware
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
        return response


app.add_middleware(TimingMiddleware)


# API routes
app.include_router(api, prefix="/api/v1")

@app.get("/")
def root(request: Request):
    """API root or SPA entry based on client accept header."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept and _frontend_dist.is_dir():
        from fastapi.responses import FileResponse
        return FileResponse(_frontend_dist / "index.html")
    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
    }


# Serve frontend static files
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA — non-API routes return index.html, API routes return 404 JSON."""
        # Never swallow API routes with SPA index.html
        if full_path.startswith("api/") or full_path == "api" or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail=f"API endpoint not found: /{full_path}")

        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await websocket.accept()
    _active_connections.append(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _active_connections.remove(websocket)
    except Exception:
        if websocket in _active_connections:
            _active_connections.remove(websocket)


async def broadcast_event(event_type: str, payload: dict):
    """Broadcast an event to all connected WebSocket clients."""
    message = {"type": event_type, "data": payload}
    disconnected = []
    for ws in list(_active_connections):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        try:
            _active_connections.remove(ws)
        except ValueError:
            pass
