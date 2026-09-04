"""
IBVAP — Computer Vision Analysis Job Endpoints
Manages video analysis lifecycle: job submission, progress querying,
cancellation, and detailed forensic results retrieval.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.analysis_job import AnalysisJob
from backend.app.models.media_asset import MediaAsset
from backend.app.models.camera import Camera
from backend.app.models.detection import Detection
from backend.app.models.incident import Incident
from backend.app.models.evidence import Evidence
from backend.app.services.video_analysis import VideoAnalysisEngine

router = APIRouter()


class CreateAnalysisJobIn(BaseModel):
    source_type: str = Field(default="upload", description="upload, rtsp, camera")
    source_id: Optional[int] = Field(default=None, description="MediaAsset ID or Camera ID")
    source_url: Optional[str] = Field(default="", description="RTSP URL or stream path")
    detector_model: Optional[str] = Field(default="yolo26n", description="yolo26n, yolo11n, motion")
    confidence_threshold: Optional[float] = Field(default=0.25, ge=0.05, le=0.95)
    zone_ids: Optional[List[int]] = Field(default=None, description="Ad-hoc zone IDs to evaluate")
    enable_anpr: Optional[bool] = Field(default=False, description="Enable automatic number plate recognition")
    enable_tracking: Optional[bool] = Field(default=True, description="Enable multi-object tracking")
    enable_behavior: Optional[bool] = Field(default=True, description="Enable behavior analytics (loitering, crowd, rapid)")
    enable_night_mode: Optional[bool] = Field(default=True, description="Enable night detection & CLAHE enhancement")
    enable_face: Optional[bool] = Field(default=False, description="Enable face detection / watchlist matching")


class AnalysisJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_id: Optional[int]
    source_url: str
    status: str
    progress_percent: float
    total_frames: int
    processed_frames: int
    detections_count: int
    incidents_count: int
    fps: float
    detector_model: str
    confidence_threshold: float
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: str
    summary: dict
    created_at: datetime


@router.post("/jobs", response_model=AnalysisJobOut, status_code=status.HTTP_201_CREATED)
def create_analysis_job(data: CreateAnalysisJobIn, db: Session = Depends(get_db)):
    """
    Create and launch an asynchronous computer vision analysis job for an uploaded video, RTSP, or camera.
    """
    # 1. Validate source existence
    source_type = "upload" if data.source_type in ("upload", "media") else data.source_type

    if source_type == "upload":
        if not data.source_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_id is required for uploaded media")
        asset = db.get(MediaAsset, data.source_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"MediaAsset #{data.source_id} not found")
    elif source_type == "camera":
        if not data.source_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_id is required for camera source")
        cam = db.get(Camera, data.source_id)
        if not cam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Camera #{data.source_id} not found")
    elif source_type == "rtsp":
        if not data.source_url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_url is required for rtsp source")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported source_type: {data.source_type}")

    # 2. Create job record
    job = AnalysisJob(
        source_type=source_type,
        source_id=data.source_id,
        source_url=data.source_url or "",
        status="queued",
        detector_model=data.detector_model or "yolo26n",
        confidence_threshold=data.confidence_threshold or 0.25,
        summary={
            "zone_ids": data.zone_ids or [],
            "enable_anpr": bool(data.enable_anpr),
            "enable_tracking": bool(data.enable_tracking),
            "enable_behavior": bool(data.enable_behavior),
            "enable_night_mode": bool(data.enable_night_mode),
            "enable_face": bool(data.enable_face),
        },
        created_by="operator",
    )
    db.add(job)
    db.commit()
    db.refresh(job)


    # 3. Launch background worker thread
    VideoAnalysisEngine.start_job(job.id)

    return job


@router.get("/jobs", response_model=List[AnalysisJobOut])
def list_analysis_jobs(db: Session = Depends(get_db)):
    """List all computer vision analysis jobs."""
    return db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=AnalysisJobOut)
def get_analysis_job(job_id: int, db: Session = Depends(get_db)):
    """Retrieve current status and progress of an analysis job."""
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return job


@router.get("/jobs/{job_id}/results")
def get_analysis_results(job_id: int, db: Session = Depends(get_db)):
    """Retrieve full analysis report including detections, incidents, and forensic evidence."""
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    detections = (
        db.query(Detection)
        .filter(Detection.job_id == job_id)
        .order_by(Detection.frame_index.asc())
        .limit(200)
        .all()
    )

    incidents = (
        db.query(Incident)
        .filter(Incident.job_id == job_id)
        .order_by(Incident.created_at.asc())
        .all()
    )

    incident_ids = [inc.id for inc in incidents]
    evidence_list = []
    if incident_ids:
        evidence_list = (
            db.query(Evidence)
            .filter(Evidence.incident_id.in_(incident_ids))
            .all()
        )

    # Source info
    source_name = "Unknown Source"
    if job.source_type == "upload" and job.source_id:
        asset = db.get(MediaAsset, job.source_id)
        if asset:
            source_name = asset.original_filename
    elif job.source_type == "camera" and job.source_id:
        cam = db.get(Camera, job.source_id)
        if cam:
            source_name = cam.name
    elif job.source_type == "rtsp":
        source_name = job.source_url

    return {
        "job_id": job.id,
        "source_name": source_name,
        "source_type": job.source_type,
        "status": job.status,
        "total_frames": job.total_frames,
        "processed_frames": job.processed_frames,
        "fps": job.fps,
        "detector_model": job.detector_model,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "summary": job.summary,
        "detections_count": job.detections_count,
        "incidents_count": job.incidents_count,
        "detections": [
            {
                "id": d.id,
                "frame": d.frame_index,
                "label": d.label,
                "confidence": d.confidence,
                "track_id": d.track_id,
                "bbox": [d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
                "bbox_x1": d.bbox_x1,
                "bbox_y1": d.bbox_y1,
                "bbox_x2": d.bbox_x2,
                "bbox_y2": d.bbox_y2,
                "timestamp_ms": d.payload.get("timestamp_ms", 0.0) if d.payload else 0.0,
                "metadata": d.payload or {},
            }
            for d in detections
        ],
        "incidents": [
            {
                "id": inc.id,
                "code": inc.incident_code,
                "title": inc.title,
                "severity": inc.severity,
                "threat_score": inc.threat_score,
                "zone_name": inc.zone_name,
                "track_ids": inc.track_ids or [],
                "status": inc.status,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
            }
            for inc in incidents
        ],
        "evidence": [
            {
                "id": ev.id,
                "incident_id": ev.incident_id,
                "sha256": ev.sha256,
                "file_path": ev.file_path,
                "filename": os.path.basename(ev.file_path),
                "threat_score": ev.threat_score,
            }
            for ev in evidence_list
        ],
    }


@router.get("/jobs/{job_id}/tracks")
def get_analysis_job_tracks(job_id: int, db: Session = Depends(get_db)):
    """
    Retrieve summarized multi-object tracks for an analysis job.
    Returns persistent track_id, class, first/last frame, downsampled normalized path,
    speed, zones touched, and night frame percentage.
    """
    import math
    from collections import Counter

    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    # Fetch frame dimensions for coordinate normalization
    frame_w = 1280
    frame_h = 720
    fps = job.fps if job.fps and job.fps > 0 else 15.0

    if job.source_type == "upload" and job.source_id:
        asset = db.get(MediaAsset, job.source_id)
        if asset and asset.width and asset.height and asset.width > 0 and asset.height > 0:
            frame_w = asset.width
            frame_h = asset.height
            if asset.fps and asset.fps > 0:
                fps = asset.fps

    # Fetch all detections for this job that have a track_id
    detections = (
        db.query(Detection)
        .filter(
            Detection.job_id == job_id,
            Detection.track_id.isnot(None),
            Detection.track_id != "",
        )
        .order_by(Detection.frame_index.asc(), Detection.id.asc())
        .all()
    )

    if not detections:
        return {"job_id": job_id, "tracks": [], "total_tracks": 0}

    # Dynamically detect frame bounds if default was used
    if frame_w == 1280 and frame_h == 720:
        max_x = max((d.bbox_x2 for d in detections), default=1280)
        max_y = max((d.bbox_y2 for d in detections), default=720)
        frame_w = max(max_x, 640)
        frame_h = max(max_y, 480)

    # Correlate incidents with tracks for zones_touched
    incidents = db.query(Incident).filter(Incident.job_id == job_id).all()
    track_zones: Dict[str, set] = {}
    for inc in incidents:
        if inc.zone_name and inc.track_ids:
            for tid in inc.track_ids:
                track_zones.setdefault(str(tid), set()).add(inc.zone_name)

    # Group detections by track_id
    track_groups: Dict[str, List[Detection]] = {}
    for d in detections:
        track_groups.setdefault(str(d.track_id), []).append(d)

    tracks_out = []
    for tid, t_dets in track_groups.items():
        if not t_dets:
            continue

        # Determine dominant class label
        classes = [d.label for d in t_dets if d.label]
        class_name = Counter(classes).most_common(1)[0][0] if classes else "unknown"

        first_frame = t_dets[0].frame_index
        last_frame = t_dets[-1].frame_index

        first_ts = (
            (t_dets[0].payload or {}).get("timestamp_ms")
            if t_dets[0].payload and "timestamp_ms" in t_dets[0].payload
            else round((first_frame / fps) * 1000.0, 1)
        )
        last_ts = (
            (t_dets[-1].payload or {}).get("timestamp_ms")
            if t_dets[-1].payload and "timestamp_ms" in t_dets[-1].payload
            else round((last_frame / fps) * 1000.0, 1)
        )

        # Centroid trajectory
        centroids = []
        speeds = []
        prev_cx = None
        prev_cy = None
        prev_t = None
        night_count = 0

        for d in t_dets:
            cx = (d.bbox_x1 + d.bbox_x2) / 2.0
            cy = (d.bbox_y1 + d.bbox_y2) / 2.0
            norm_x = round(min(1.0, max(0.0, cx / frame_w)), 4)
            norm_y = round(min(1.0, max(0.0, cy / frame_h)), 4)
            centroids.append([norm_x, norm_y, d.frame_index])

            t_ms = (
                (d.payload or {}).get("timestamp_ms")
                if d.payload and "timestamp_ms" in d.payload
                else (d.frame_index / fps) * 1000.0
            )

            if prev_cx is not None and prev_cy is not None and prev_t is not None:
                dt_sec = max(0.001, (t_ms - prev_t) / 1000.0)
                px_dist = math.sqrt((cx - prev_cx) ** 2 + (cy - prev_cy) ** 2)
                speed = px_dist / dt_sec
                speeds.append(speed)

            prev_cx = cx
            prev_cy = cy
            prev_t = t_ms

            if (d.payload or {}).get("night"):
                night_count += 1

        # Downsample trajectory if exceptionally dense
        if len(centroids) > 100:
            step = max(1, len(centroids) // 80)
            downsampled_path = centroids[::step]
            if downsampled_path[-1] != centroids[-1]:
                downsampled_path.append(centroids[-1])
        else:
            downsampled_path = centroids

        max_speed = round(max(speeds), 1) if speeds else 0.0
        night_pct = round((night_count / len(t_dets)) * 100.0, 1)
        zones = sorted(list(track_zones.get(str(tid), set())))

        tracks_out.append({
            "track_id": tid,
            "class": class_name,
            "first_frame": first_frame,
            "last_frame": last_frame,
            "first_timestamp_ms": first_ts,
            "last_timestamp_ms": last_ts,
            "path": downsampled_path,
            "points_count": len(downsampled_path),
            "max_speed": max_speed,
            "zones_touched": zones,
            "night_frame_pct": night_pct,
            "detections_count": len(t_dets),
        })

    # Sort tracks by first_frame asc
    tracks_out.sort(key=lambda x: x["first_frame"])

    return {
        "job_id": job_id,
        "tracks": tracks_out,
        "total_tracks": len(tracks_out),
    }



@router.post("/jobs/{job_id}/cancel")
def cancel_analysis_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel an ongoing analysis job."""
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    cancelled = VideoAnalysisEngine.cancel_job(job_id)
    if not cancelled and job.status == "processing":
        job.status = "cancelled"
        db.commit()

    return {"cancelled": True, "job_id": job_id}


@router.get("/jobs/{job_id}/report")
def export_analysis_job_report(
    job_id: int,
    format: str = Query("json", pattern="^(json|pdf)$"),
    db: Session = Depends(get_db),
):
    """Export comprehensive forensic & tactical report for an analysis job in JSON or PDF format."""
    from fastapi.responses import Response
    from backend.app.services.report import build_report_data, generate_pdf_report

    try:
        data = build_report_data(job_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if format.lower() == "pdf":
        pdf_bytes = generate_pdf_report(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="ibvap_report_job_{job_id}.pdf"',
                "X-Statutory-Authority": "Bharatiya Sakshya Adhiniyam, 2023 Section 63",
            },
        )

    return data

