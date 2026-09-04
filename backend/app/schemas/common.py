"""
Pydantic schemas for API request/response contracts.
Python 3.9 compatible — uses Optional[] from typing.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    full_name: str = ""
    active: bool
    model_config = ConfigDict(from_attributes=True)


# ── Camera ────────────────────────────────────────────────────

class CameraIn(BaseModel):
    name: str
    stream_url: str
    location: str = "Unknown"
    bop: str = "BOP-01"
    sector: Optional[str] = "Sector Alpha"
    camera_type: str = "IP"
    fps: int = 10
    resolution: str = "1280x720"
    latitude: float = 0.0
    longitude: float = 0.0
    analytics_enabled: bool = True
    detection_interval: int = 3
    description: str = ""


class CameraPatchIn(BaseModel):
    name: Optional[str] = None
    stream_url: Optional[str] = None
    location: Optional[str] = None
    bop: Optional[str] = None
    sector: Optional[str] = None
    camera_type: Optional[str] = None
    fps: Optional[int] = None
    resolution: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    analytics_enabled: Optional[bool] = None
    detection_interval: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None


class CameraOut(CameraIn, ORMModel):
    id: int
    status: str
    health_score: float
    last_heartbeat: Optional[datetime] = None
    max_inference_fps: int = 5
    active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


# ── Zone ──────────────────────────────────────────────────────

class ZoneIn(BaseModel):
    camera_id: Optional[int] = None
    name: str
    zone_type: str = "RESTRICTED"
    geometry: Optional[Dict[str, Any]] = None
    polygon: Optional[List[List[float]]] = None
    direction: str = "either"
    armed_schedule: Optional[Dict[str, Any]] = None
    night_only: bool = False
    min_confidence: float = 0.25
    enabled: bool = True
    active: bool = True
    severity: float = 0.5
    dwell_threshold_seconds: int = 30
    color: str = ""
    description: str = ""
    created_by: Optional[str] = "operator"

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("either", "a_to_b", "b_to_a"):
            raise ValueError("direction must be one of: either, a_to_b, b_to_a")
        return v

    @field_validator("min_confidence")
    @classmethod
    def validate_min_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_and_reconcile_geometry(self):
        geom = self.geometry
        poly = self.polygon

        if geom is None and not poly:
            raise ValueError("Either 'geometry' or 'polygon' must be provided")

        if geom is not None:
            g_type = geom.get("type")
            if g_type not in ("line", "polygon"):
                raise ValueError("geometry.type must be 'line' or 'polygon'")
            pts = geom.get("points")
            if not isinstance(pts, list):
                raise ValueError("geometry.points must be a list of coordinates")
            if g_type == "line" and len(pts) < 2:
                raise ValueError("Line geometry requires at least 2 points")
            if g_type == "polygon" and len(pts) < 3:
                raise ValueError("Polygon geometry requires at least 3 points")
            for pt in pts:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    raise ValueError("Each point must have at least 2 coordinates [x, y]")
                x, y = float(pt[0]), float(pt[1])
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    raise ValueError(f"Coordinates must be normalized within [0.0, 1.0], got ({x}, {y})")
            if not poly:
                self.polygon = pts
        elif poly is not None:
            if len(poly) < 3:
                raise ValueError("Polygon requires at least 3 points")
            for pt in poly:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    raise ValueError("Each point must have at least 2 coordinates [x, y]")
                x, y = float(pt[0]), float(pt[1])
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    raise ValueError(f"Coordinates must be normalized within [0.0, 1.0], got ({x}, {y})")
            self.geometry = {"type": "polygon", "points": poly}

        self.enabled = self.active if self.enabled is None else self.enabled
        self.active = self.enabled
        return self


class ZonePatchIn(BaseModel):
    camera_id: Optional[int] = None
    name: Optional[str] = None
    zone_type: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    polygon: Optional[List[List[float]]] = None
    direction: Optional[str] = None
    armed_schedule: Optional[Dict[str, Any]] = None
    night_only: Optional[bool] = None
    min_confidence: Optional[float] = None
    enabled: Optional[bool] = None
    active: Optional[bool] = None
    severity: Optional[float] = None
    dwell_threshold_seconds: Optional[int] = None
    color: Optional[str] = None
    description: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("either", "a_to_b", "b_to_a"):
            raise ValueError("direction must be one of: either, a_to_b, b_to_a")
        return v

    @field_validator("min_confidence")
    @classmethod
    def validate_min_confidence(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_geometry(self):
        if self.geometry is not None:
            g_type = self.geometry.get("type")
            if g_type not in ("line", "polygon"):
                raise ValueError("geometry.type must be 'line' or 'polygon'")
            pts = self.geometry.get("points")
            if not isinstance(pts, list):
                raise ValueError("geometry.points must be a list")
            if g_type == "line" and len(pts) < 2:
                raise ValueError("Line geometry requires at least 2 points")
            if g_type == "polygon" and len(pts) < 3:
                raise ValueError("Polygon geometry requires at least 3 points")
            for pt in pts:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    raise ValueError("Each point must have at least 2 coordinates [x, y]")
                x, y = float(pt[0]), float(pt[1])
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    raise ValueError(f"Coordinates must be normalized within [0.0, 1.0], got ({x}, {y})")
        return self


class ZoneOut(ORMModel):
    id: int
    camera_id: Optional[int] = None
    name: str
    zone_type: str = "RESTRICTED"
    geometry: Dict[str, Any] = Field(default_factory=dict)
    polygon: List[List[float]] = Field(default_factory=list)
    direction: str = "either"
    armed_schedule: Optional[Dict[str, Any]] = None
    night_only: bool = False
    min_confidence: float = 0.25
    enabled: bool = True
    active: bool = True
    severity: float = 0.5
    dwell_threshold_seconds: int = 30
    color: str = ""
    description: str = ""
    created_by: Optional[str] = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Detection ─────────────────────────────────────────────────

class DetectionOut(ORMModel):
    id: int
    camera_id: int
    track_id: Optional[str] = None
    label: str
    confidence: float
    bbox_x1: int
    bbox_y1: int
    bbox_x2: int
    bbox_y2: int
    frame_index: int
    source: str
    detected_at: datetime


# ── Track ─────────────────────────────────────────────────────

class TrackOut(ORMModel):
    id: int
    camera_id: int
    track_id: str
    label: str
    confidence_avg: float
    first_seen: datetime
    last_seen: datetime
    active: bool
    trajectory: List[Any] = []
    dwell_time_seconds: float
    speed_estimate: float
    direction: str
    zone_ids: List[Any] = []
    current_zone_id: Optional[int] = None
    frame_count: int
    last_bbox: Dict[str, Any] = {}


# ── Event ─────────────────────────────────────────────────────

class EventOut(ORMModel):
    id: int
    camera_id: int
    event_type: str
    object_type: str
    track_id: Optional[str] = None
    confidence: float
    zone_id: Optional[int] = None
    severity: float
    payload: Dict[str, Any] = {}
    occurred_at: datetime


# ── Incident ──────────────────────────────────────────────────

class IncidentOut(ORMModel):
    id: int
    incident_code: str
    title: str
    description: str = ""
    severity: str
    threat_score: float
    confidence: float = 0.0
    status: str
    reason_codes: List[Any] = []
    event_ids: List[Any] = []
    detection_ids: List[Any] = []
    track_ids: List[Any] = []
    camera_id: Optional[int] = None
    camera_name: str = ""
    zone_name: str = ""
    fingerprint: str = ""
    correlated_ids: List[Any] = []
    recommended_action: str = ""
    ai_assessment: Dict[str, Any] = {}
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    escalated_by: Optional[str] = None
    timeline: List[Any] = []


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    notes: str = ""


# ── Alert ─────────────────────────────────────────────────────

class AlertOut(ORMModel):
    id: int
    incident_id: int
    priority: str
    status: str
    message: str = ""
    created_at: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


# ── Evidence ──────────────────────────────────────────────────

class EvidenceOut(ORMModel):
    id: int
    incident_id: int
    evidence_type: str = "snapshot"
    file_path: str
    sha256: str
    manifest_path: str
    manifest_data: Dict[str, Any] = {}
    file_size_bytes: int = 0
    threat_score: float = 0.0
    camera_id: Optional[int] = None
    camera_name: str = ""
    detection_metadata: Dict[str, Any] = {}
    created_at: datetime


class EvidenceVerification(BaseModel):
    valid: bool
    sha256: str
    manifest_path: str
    verified_at: str


# ── Audit ─────────────────────────────────────────────────────

class AuditLogOut(ORMModel):
    id: int
    actor: str
    actor_role: str = ""
    action: str
    target_type: str
    target_id: str
    details: Dict[str, Any] = {}
    ip_address: str = ""
    previous_hash: str = ""
    entry_hash: str = ""
    created_at: datetime


# ── Sync ──────────────────────────────────────────────────────

class SyncQueueOut(ORMModel):
    id: int
    event_key: str
    status: str
    event_type: str
    camera_id: Optional[int] = None
    attempts: int
    created_at: datetime
    error_message: str = ""


# ── Camera Health ─────────────────────────────────────────────

class CameraHealthOut(ORMModel):
    id: int
    camera_id: int
    health_score: float
    status: str
    fps_actual: float
    brightness: float
    blur_score: float
    frame_delta: float
    resolution_width: int = 0
    resolution_height: int = 0
    latency_ms: float = 0.0
    measured_at: datetime


# ── System ────────────────────────────────────────────────────

class SystemStatus(BaseModel):
    status: str
    version: str
    uptime_seconds: float = 0.0
    cameras_online: int = 0
    cameras_total: int = 0
    active_incidents: int = 0
    active_alerts: int = 0
    edge_nodes: int = 0
    sync_pending: int = 0
    events_today: int = 0


class MetricsOut(BaseModel):
    camera_fps: Dict[str, int] = {}
    cameras_online: int = 0
    cameras_total: int = 0
    frames_processed: int = 0
    detections_total: int = 0
    tracks_active: int = 0
    incidents_total: int = 0
    alerts_total: int = 0
    processing_latency_ms: float = 0.0
    queue_depth: int = 0
    sync_failures: int = 0


# ── Demo ──────────────────────────────────────────────────────

class DemoRequest(BaseModel):
    camera_id: int = 1
    scenario: str = "intrusion"


class DemoScenarioOut(BaseModel):
    id: str
    name: str
    description: str
    severity: str
