# IBVAP Architecture

## System Overview

IBVAP follows an edge-first, modular architecture designed for border surveillance using existing CCTV infrastructure.

```
┌─────────────────────────────────────────────────────────┐
│                    COMMAND CENTER UI                      │
│  Dashboard │ Cameras │ Incidents │ Evidence │ Audit │ Map │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket / REST API
┌──────────────────────────┴──────────────────────────────┐
│                    BACKEND API (FastAPI)                  │
│  Auth │ Cameras │ Zones │ Incidents │ Evidence │ Demo    │
│  Scoring │ Correlation │ Audit │ Sync │ Metrics          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│                    DATABASE (SQLite/PostgreSQL)           │
│  Users │ Cameras │ Zones │ Detections │ Tracks │ Events  │
│  Incidents │ Alerts │ Evidence │ AuditLogs │ SyncQueue   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│                    EDGE PIPELINE                          │
│  Video Source → Detection → Tracking → Zones → Behavior  │
│  → Context Engine → Scoring → Evidence → Queue           │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│                    VIDEO SOURCES                          │
│  RTSP │ ONVIF │ Webcam │ Uploaded Video │ Demo/Synthetic │
└─────────────────────────────────────────────────────────┘
```

## Edge Pipeline Detail

```
Frame Sampling
    ↓
Background Subtraction (MOG2) / Detector Adapter
    ↓
Connected Components → Detections
    ↓
IoU Matching → Track Assignment
    ↓
Position Update → Trajectory, Direction, Speed
    ↓
Zone Membership Check → Entry/Exit/Crossing Events
    ↓
Behavior Analysis → Loitering, Night, Abandoned, Rapid
    ↓
Context Fusion → Enriched Events
    ↓
Threat Scoring → Score + Severity + Reasons + Confidence
    ↓
Evidence Capture → SHA-256 Manifest + Hash Chain
```

## Scoring Architecture

The threat scoring engine is transparent and configurable:

```
Signal Weights (configurable):
  confidence:              12
  zone_severity:           25
  boundary_crossing:       18
  loitering:               12
  night:                    8
  vehicle_context:          5
  behavior_anomaly:        10
  repeated_activity:        5
  camera_health_degraded:   2
  cross_camera_corroboration: 3
                           ───
                           100

Score ≥ 85 → CRITICAL
Score ≥ 65 → HIGH
Score ≥ 40 → MEDIUM
Score < 40 → LOW
```

## Data Flow

1. **Detection** → `Detection` record (label, confidence, bbox, source)
2. **Tracking** → `Track` record (trajectory, dwell, direction, speed, zones)
3. **Zone Event** → `Event` record (zone_entry, zone_exit, zone_crossing)
4. **Behavior** → `Event` record (loitering, night_movement, abandoned_object)
5. **Scoring** → `ThreatAssessment` (score, severity, confidence, reasons)
6. **Incident** → `Incident` record (code, title, severity, score, timeline, AI assessment)
7. **Alert** → `Alert` record (priority, status, message)
8. **Evidence** → `Evidence` record (SHA-256 hash, manifest, chain)
9. **Audit** → `AuditLog` record (actor, action, target, hash chain)

## Deployment Modes

| Mode | Description |
|------|-------------|
| Local Demo | SQLite + in-process event bus |
| Docker | PostgreSQL + Redis + API + Frontend |
| Edge Node | Lightweight pipeline near CCTV source |
| Multi-Node | Multiple edge nodes + central command |

## Scalability Strategy

```
Camera → Edge Node → Event Bus → Central Command
   1        1           1            1
  10        2           1            1
 100        5-10        Redis        1
```

Each edge node processes cameras locally. The central command aggregates events, incidents, and evidence from multiple edge nodes.
