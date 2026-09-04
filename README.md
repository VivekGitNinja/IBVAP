# IBVAP — Intelligent Border Video Analytics Platform

**Smart India Hackathon 2026 • Problem Statement 26187**
Ministry of Home Affairs / Sashastra Seema Bal (SSB)

A local-first, edge-oriented video analytics platform that turns CCTV observations into explainable, prioritized incidents while keeping a human operator in the loop.

## Architecture

```
CCTV / RTSP / ONVIF / Webcam / Demo Video
        ↓
Video Ingestion + Frame Sampling
        ↓
Pluggable AI Perception (Motion / YOLO / ONNX)
        ↓
Object Tracking (IoU-based multi-object)
        ↓
Virtual Fence / Zone Engine
        ↓
Behavior Intelligence (loitering, crossing, abandoned, night)
        ↓
Context Engine (multi-signal fusion)
        ↓
Explainable Threat Scoring
        ↓
Incident Generation + Alert Deduplication
        ↓
Evidence Capture + SHA-256 Integrity
        ↓
Human Verification (Acknowledge / Escalate / Dismiss)
        ↓
Command Center Dashboard
```

## Quick Start

### Option 1: Local Development (Recommended)

```bash
# 1. Clone and setup
cd ibvap
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Configure
cp .env.example .env

# 3. Start backend
PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8000

# 4. In another terminal, start frontend
cd frontend && npm install && npm run dev
```

Open:
- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- API root: http://localhost:8000

### Option 2: Docker Compose

```bash
docker compose up --build
```

### Run Demo

```bash
# Seed demo incidents via API
curl -X POST http://localhost:8000/api/v1/demo/seed?scenario=intrusion

# Or seed all scenarios
curl -X POST http://localhost:8000/api/v1/demo/seed/all
```

Or click "Run Demo" in the dashboard.

## Default Credentials

| Username   | Password      | Role      |
|-----------|---------------|-----------|
| admin     | admin123      | ADMIN     |
| commander | commander123  | COMMANDER |
| operator  | operator123   | OPERATOR  |

## Features

### ✅ Implemented
- **Object Detection**: Pluggable adapter (motion-based CPU fallback, YOLO/ONNX-ready)
- **Object Tracking**: IoU-based multi-object tracker with persistent IDs, trajectory, dwell time, direction, speed
- **Virtual Fence**: Polygon zones (RESTRICTED, SENSITIVE, PATROL, MONITORING, EXCLUSION)
- **Behavior Intelligence**: Loitering, boundary crossing, rapid movement, night movement, abandoned object, repeated crossing
- **Explainable Threat Scoring**: Multi-signal weighted scoring with full explanation and recommended actions
- **Incident Management**: Full lifecycle (OPEN → ACKNOWLEDGED → ESCALATED → CLOSED/DISMISSED)
- **Evidence Engine**: SHA-256 manifest sealing, integrity verification, hash chain
- **Audit Trail**: Tamper-evident audit log with hash chaining
- **Offline Store-and-Forward**: Event queue for edge-first operation
- **Camera Health Intelligence**: Brightness, blur, freeze detection, FPS monitoring
- **Multi-Camera Correlation**: Temporal and spatial event correlation
- **Alert Deduplication**: Incident fingerprinting, cooldown, event aggregation
- **Demo Scenario Engine**: 6 deterministic demo scenarios
- **Command Center UI**: Professional dark-themed dashboard with all views
- **JWT Authentication**: Role-based access control (ADMIN/COMMANDER/OPERATOR/AUDITOR/VIEWER)
- **WebSocket Events**: Real-time event streaming
- **Security Headers**: XSS, CSRF, content-type protection
- **104 Unit/API/Integration Tests**: Scoring, geometry, tracking, zones, evidence, demo, audit, system integrity (0 warnings, 100% passing)

### ⚠️ Honest Fallbacks (Not Faked)
- **CPU Demo Mode**: Motion-based perception fallback (not semantic AI detection)
- **ANPR**: Adapter interface ready, demo fallback only
- **Face Analytics**: Adapter interface ready, not implemented as autonomous identification
- **GPU Acceleration**: Architecture supports it, not required for demo

## Demo Scenarios

| ID | Name | Severity | Description |
|----|------|----------|-------------|
| intrusion | Restricted Zone Intrusion | CRITICAL | Person enters restricted border zone |
| night_movement | Night-Time Movement | HIGH | Suspicious movement during night hours |
| loitering | Extended Loitering | MEDIUM | Object stationary near boundary |
| vehicle | Vehicle Near Restricted Zone | HIGH | Vehicle approaching restricted perimeter |
| abandoned | Abandoned Object | HIGH | Object left stationary after person departs |
| multi_camera | Multi-Camera Correlated | CRITICAL | Events correlated across multiple cameras |

## API Endpoints

- `GET /api/v1/health` — Health check
- `GET /api/v1/status` — System status
- `POST /api/v1/auth/token` — Login
- `GET/POST /api/v1/cameras` — Camera management
- `GET/POST /api/v1/zones` — Zone management
- `GET /api/v1/events` — Event listing
- `GET/POST /api/v1/incidents` — Incident management
- `POST /api/v1/incidents/{id}/acknowledge` — Acknowledge
- `POST /api/v1/incidents/{id}/escalate` — Escalate
- `GET /api/v1/incidents/{id}/timeline` — Incident timeline
- `GET /api/v1/evidence/{id}` — Evidence listing
- `GET /api/v1/evidence/verify/{id}` — Evidence verification
- `GET /api/v1/audit` — Audit trail
- `GET /api/v1/metrics` — System metrics
- `GET /api/v1/sync/status` — Sync queue status
- `POST /api/v1/demo/seed` — Generate demo incident
- `WebSocket /ws/events` — Real-time events

## Innovation Points (SIH 2026)

1. **Adaptive Edge Intelligence** — Processing near CCTV source
2. **Explainable Threat Scoring** — Every score has reasons and confidence
3. **Multi-Signal Incident Correlation** — Combines detection, zone, behavior, context
4. **Multi-Camera Event Correlation** — Temporal/spatial correlation across cameras
5. **Privacy-Preserving Analytics** — Candidate matching only, no autonomous identification
6. **Human-in-the-Loop Verification** — AI recommends, human decides
7. **Offline-First Store-and-Forward** — Operates without backend connectivity
8. **Tamper-Evident Evidence** — SHA-256 hash chain integrity
9. **Camera Health Intelligence** — Blur, freeze, brightness, FPS monitoring
10. **Alert Deduplication** — Prevents alert storms
11. **Rule + AI Hybrid Reasoning** — Perception + rules + correlation + scoring
12. **Adaptive Inference** — Frame sampling, ROI processing
13. **Evidence-Centric Timeline** — Complete incident lifecycle
14. **Existing-CCTV-First** — Works with RTSP, ONVIF, webcam, uploaded video
15. **Hardware-Agnostic Edge** — CPU-first, GPU-optional

## Privacy Policy

See [PRIVACY.md](docs/privacy.md) for privacy documentation.

## Limitations

See [docs/limitations.md](docs/limitations.md) for known limitations.

## License

Prototype for Smart India Hackathon 2026. See individual model licenses in MODEL_LICENSES.md.
