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

import uuid
from backend.app.db.session import engine, SessionLocal
from backend.app.db.base import Base
from backend.app.db.migrator import run_database_migrations
from backend.app.api.v1.router import api
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, get_logger, set_trace_id, get_trace_id
from backend.app.core.metrics import (
    record_http_request,
    record_detection,
    set_active_ws_count,
    generate_metrics_text,
)
from backend.app.models.user import User
from backend.app.models.camera import Camera
from backend.app.core.security import hash_password, decode_access_token
from backend.app.services.live_pipeline import live_manager
from backend.app.services.video_analysis import (
    set_analysis_event_loop,
    register_job_subscriber,
    unregister_job_subscriber,
)

logger = setup_logging(log_level=settings.log_level, json_format=(settings.log_format == "json"))

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
    set_analysis_event_loop(_event_loop)

    # Create and synchronize tables and performance indexes
    migration_summary = run_database_migrations(engine)
    logger.info(
        "Database schema synchronized",
        extra={
            "tables_count": migration_summary["tables_count"],
            "indexes_verified": migration_summary["indexes_verified"],
        }
    )

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

        # Create demo cameras only if explicitly enabled in configuration
        if settings.enable_demo and settings.enable_synthetic_cameras and db.query(Camera).count() == 0:
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
            try:
                record_detection(event.get("type", "detection"), event.get("camera_id", ""))
            except Exception:
                pass
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
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
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


# Observability & Distributed Tracing Middleware
class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or generate distributed Trace ID
        trace_id = (
            request.headers.get("X-Trace-ID")
            or request.headers.get("X-Request-ID")
            or f"ibvap-{uuid.uuid4().hex[:12]}"
        )
        set_trace_id(trace_id)

        start = time.time()
        path = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            elapsed_sec = time.time() - start
            elapsed_ms = elapsed_sec * 1000.0

            # Inject trace ID and process time in headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"

            # Record Prometheus metrics (skip /metrics itself to prevent loop inflation)
            if path != "/metrics":
                record_http_request(
                    method=method,
                    path=path,
                    status=response.status_code,
                    duration_seconds=elapsed_sec,
                )

            # Emit structured JSON log for non-static assets
            if not path.startswith("/assets") and path != "/favicon.ico":
                client_ip = request.client.host if request.client else "unknown"
                logger.info(
                    f"{method} {path} HTTP/{request.scope.get('http_version', '1.1')} {response.status_code} ({elapsed_ms:.1f}ms)",
                    extra={
                        "trace_id": trace_id,
                        "method": method,
                        "path": path,
                        "status_code": response.status_code,
                        "duration_ms": round(elapsed_ms, 2),
                        "client_ip": client_ip,
                    },
                )

            return response
        except Exception as exc:
            elapsed_sec = time.time() - start
            elapsed_ms = elapsed_sec * 1000.0
            record_http_request(method=method, path=path, status=500, duration_seconds=elapsed_sec)
            logger.error(
                f"Unhandled server error on {method} {path}: {str(exc)}",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )
            raise


app.add_middleware(ObservabilityMiddleware)


# Prometheus metrics exposition endpoint
@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    """
    Expose RFC-compliant Prometheus/OpenMetrics exposition format (0.0.4)
    telemetry counters, gauges, and latency histograms for Prometheus scrapers.
    """
    from fastapi.responses import Response
    return Response(
        content=generate_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


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


# Initialize evidence directory
_clips_dir = Path(settings.evidence_dir) / "clips"
_clips_dir.mkdir(parents=True, exist_ok=True)
if Path(settings.evidence_dir).is_dir():
    app.mount("/data/evidence", StaticFiles(directory=settings.evidence_dir), name="evidence_static")

# Serve frontend static files
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Never swallow API routes or metrics with SPA index.html
        if full_path.startswith("api/") or full_path == "api" or full_path.startswith("ws/") or full_path == "metrics":
            raise HTTPException(status_code=404, detail=f"Endpoint not found: /{full_path}")

        # Strict path traversal prevention
        try:
            dist_root = _frontend_dist.resolve()
            target_path = (_frontend_dist / full_path).resolve()
            if not str(target_path).startswith(str(dist_root)):
                raise HTTPException(status_code=403, detail="Access denied: Path traversal detected")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid path")

        if target_path.is_file():
            return FileResponse(target_path)

        # Do not serve index.html for missing files with known system/code extensions
        last_segment = full_path.split("/")[-1]
        if "." in last_segment or full_path.startswith("etc/") or full_path.startswith("var/"):
            raise HTTPException(status_code=404, detail=f"Resource not found: /{full_path}")

        return FileResponse(_frontend_dist / "index.html")


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events. Requires valid JWT token."""
    token = websocket.query_params.get("token")
    if settings.require_auth:
        if not token:
            await websocket.close(code=1008, reason="Authentication required")
            return
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=1008, reason="Invalid token")
            return

    await websocket.accept()
    _active_connections.append(websocket)
    set_active_ws_count(len(_active_connections))
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if websocket in _active_connections:
            _active_connections.remove(websocket)
            set_active_ws_count(len(_active_connections))
    except Exception:
        if websocket in _active_connections:
            _active_connections.remove(websocket)
            set_active_ws_count(len(_active_connections))


@app.websocket("/ws/analysis/{job_id}")
async def websocket_analysis_job(websocket: WebSocket, job_id: int):
    """
    Real-time WebSocket connection streaming progress, detections,
    and incidents for a specific computer vision analysis job.
    """
    token = websocket.query_params.get("token")
    if settings.require_auth and token:
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=1008, reason="Invalid token")
            return

    await websocket.accept()
    register_job_subscriber(job_id, websocket)

    # Immediately push current job status upon connection
    db = SessionLocal()
    try:
        from backend.app.models.analysis_job import AnalysisJob
        job = db.get(AnalysisJob, job_id)
        if job:
            await websocket.send_json({
                "event": "job_progress",
                "job_id": job.id,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "processed_frames": job.processed_frames,
                "total_frames": job.total_frames,
                "detections_count": job.detections_count,
                "incidents_count": job.incidents_count,
                "fps": job.fps,
            })
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        unregister_job_subscriber(job_id, websocket)


@app.websocket("/ws/live/{camera_id}")
async def websocket_live_stream(websocket: WebSocket, camera_id: int):
    """
    High-performance binary WebSocket live video stream.
    Streams JPEG frames directly as binary packets, completely bypassing browser
    HTTP/1.1 6-connection limits for unlimited concurrent camera grids.
    Requires valid JWT token.
    """
    token = websocket.query_params.get("token")
    if settings.require_auth:
        if not token:
            await websocket.close(code=1008, reason="Authentication required")
            return
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=1008, reason="Invalid token")
            return

    await websocket.accept()
    try:
        import cv2
        from backend.app.models.camera import Camera
        from backend.app.api.v1.endpoints.cameras import stream_manager, _generate_tactical_frame, _generate_offline_frame

        db = SessionLocal()
        cam = db.get(Camera, camera_id)
        db.close()

        if not cam:
            await websocket.close(code=1008, reason="Camera not found")
            return

        url = cam.stream_url or ""
        fps = max(5, min(25, cam.fps or 15))
        interval = 1.0 / fps
        frame_idx = 0

        while True:
            frame_idx += 1
            raw = None
            if not url.startswith("demo://") and url:
                raw = stream_manager.get_frame(url)

            if raw is None:
                if settings.enable_demo and settings.enable_synthetic_cameras:
                    raw = _generate_tactical_frame(cam, frame_idx)
                else:
                    raw = _generate_offline_frame(cam)

            ret, jpeg = cv2.imencode(".jpg", raw, [cv2.IMWRITE_JPEG_QUALITY, 68])
            if ret:
                await websocket.send_bytes(jpeg.tobytes())

            await asyncio.sleep(interval)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        pass


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
