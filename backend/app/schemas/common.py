"""
Pydantic schemas for API request/response contracts.
Python 3.9 compatible — uses Optional[] from typing.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


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
    camera_type: str = "IP"
    fps: int = 10
    resolution: str = "1280x720"
    latitude: float = 0.0
    longitude: float = 0.0
    analytics_enabled: bool = True
    detection_interval: int = 3
    description: str = ""


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
    camera_id: int
    name: str
    zone_type: str = "RESTRICTED"
    polygon: List[List[float]] = []
    active: bool = True
    severity: float = 0.5
    dwell_threshold_seconds: int = 30
    color: str = ""
    description: str = ""


class ZoneOut(ZoneIn, ORMModel):
    id: int
    created_at: Optional[datetime] = None


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
