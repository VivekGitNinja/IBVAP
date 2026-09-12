# IBVAP — Intelligent Border Video Analytics Platform

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH%202026-Problem%20Statement%2026187-blue.svg)](https://www.sih.gov.in/)
[![Agency](https://img.shields.io/badge/Agency-MHA%20%2F%20SSB-red.svg)](https://ssb.gov.in/)
[![Tests](https://img.shields.io/badge/Tests-188%2F188%20Passing%20(100%25)-brightgreen.svg)]()
[![Compliance](https://img.shields.io/badge/Compliance-BSA%202023%20Section%2063-orange.svg)]()
[![Air-Gapped](https://img.shields.io/badge/Deployment-Air--Gapped%20%2F%20Edge--Ready-success.svg)]()
[![AI Perception](https://img.shields.io/badge/AI-YOLO26%20%7C%20SFace%20%7C%20Tesseract-purple.svg)]()

> **Intelligent Edge Video Analytics & C4ISR Command Platform for Border Outposts (BOPs)**  
> Developed for **Smart India Hackathon 2026** under Problem Statement **PS-26187**  
> **Stakeholders:** Ministry of Home Affairs (MHA) & Sashastra Seema Bal (SSB)

---

## Executive Overview

**IBVAP** is an air-gapped, edge-first tactical video analytics platform engineered to safeguard international borders, riverine gaps, and remote border outposts (BOPs). Operating entirely on local edge hardware without cloud or external network reliance, IBVAP ingests live CCTV, RTSP camera streams, PTZ feeds, drone footage, and recorded surveillance media to extract real-time intelligence.

Unlike conventional analytics systems that overwhelm operators with noisy alerts, IBVAP pairs **neural edge perception** with **explainable threat scoring** and a **BSA 2023 (Section 63) tamper-evident evidence vault**, ensuring human commanders retain complete verification and actionable tactical clarity.

---

## Key System Architecture

```
                               ┌─────────────────────────────────────────────────────────┐
                               │                 EDGE SENSOR INGESTION                   │
                               │  Hardware Webcam (usb://0) • RTSP Feeds • Video Files   │
                               └────────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │               MULTI-ENGINE AI PERCEPTION                │
                               │  • YOLO26n / YOLO11 Edge Object Detection (Ultralytics) │
                               │  • YuNet + SFace 128D Biometric Facial Recognition      │
                               │  • HSRP ANPR OCR (Morphological + Indian Plate Regex)   │
                               │  • Zero-DCE++ / CLAHE Night Vision Low-Luma Enhancement │
                               └────────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │             SPATIAL & BEHAVIORAL TRACKING               │
                               │  • ByteTrack Centroid Tracking (Persistent ID & Trails) │
                               │  • Virtual Fence (Tripwire Lines & Exclusion Polygons)  │
                               │  • Dwell-Time, Loitering, Speed & Abandoned Object Rules│
                               └────────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │           THREAT FUSION & EXPLAINABLE SCORING           │
                               │  Multi-Signal Weighted Heuristic (0–100 Threat Index)   │
                               │  Deduplication • Cooldown Suppression • Correlated IDs  │
                               └────────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │         BSA 2023 SECTION 63 LEGAL EVIDENCE VAULT        │
                               │  • Cryptographic SHA-256 Hashing of Clips & Snapshots   │
                               │  • Chain-of-Custody Manifests (.json) & PDF Certificate │
                               └────────────────────────────┬────────────────────────────┘
                                                            │
                                                            ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │             C4ISR TACTICAL COMMAND CONSOLE              │
                               │  Real-Time WebSocket • GIS Geospatial Map • QRT Dispatch│
                               │  ANPR Intercept Barrier Control • FRS Suspect Dossiers  │
                               └─────────────────────────────────────────────────────────┘
```

---

## Core Capabilities & Intelligence Modules

### 1. Neural Edge Perception & Detection
* **YOLO26n / YOLO11 Backbones**: Pre-cached PyTorch & ONNX neural networks for real-time person, vehicle, and suspicious object detection with high precision.
* **Low-Luma Night Enhancement**: Automatic mean luma monitoring ($<60\text{ lux}$) triggers adaptive CLAHE and Zero-DCE++ enhancement for clear nocturnal surveillance.
* **Zero Fake Cameras**: Dedicated to real video feeds—streams live from Mac FaceTime HD / USB `/dev/video0` webcams, industrial RTSP cameras, or recorded field assets.

### 2. Facial Recognition System (FRS) Biometrics
* **OpenCV YuNet + SFace (128D Embeddings)**: Fast edge face localization combined with deep facial feature extraction.
* **Watchlist Suspect Gallery**: Instant cosine-similarity comparison against enrolled suspects (e.g. watchlist dossiers).
* **Live Camera Biometric Overlay**: Displays target bounding boxes with match confidence (`MATCH: <name> (XX%)`) in real time.
* **Anti-Spam Incident Cooldown**: 15-second debounce window prevents operator fatigue while guaranteeing immediate `CRITICAL` alert escalation upon suspect identification.
* **Photo Probe Verification**: Forensic upload interface for rapid one-to-many biometric database queries with legal BSA citations.

### 3. High-Speed ANPR Checkpost Terminal
* **Indian HSRP Compliance**: Tailored OCR engine for High Security Registration Plates (HSRP) across all Indian states and Union Territories (e.g., `JK`, `DL`, `UP`, `KA`, `PB`, `MH`).
* **Intelligent Character Ambiguity Repair**: Resolves typical OCR confusions (`O/0`, `I/1`, `S/5`, `B/8`, `Z/2`) based on strict RTO code and series positions.
* **Stolen Vehicle Intercept**: Automatic cross-referencing with `WATCHLIST_DB` flags stolen vehicles, trips automated barrier control (`INTERCEPT_ENGAGED`), and triggers audible tactical sirens.
* **Multi-Input Ingestion**: Works via instant image upload, checkpost passing simulator, or automated extraction from CCTV video footage.

### 4. Surveillance Video Studio (Offline Media Analysis)
* **Asynchronous CV Job Runner**: Deep frame-by-frame analysis of uploaded video assets (`.mp4`, `.mov`, `.avi`, `.webm`) with automatic H.264 transcoding.
* **Full Intelligence Pipeline**: Integrates object tracking, virtual fence breaches, ANPR plate extraction, FRS face verification, and tactical behavior rules.
* **Real-Time Job Telemetry**: Streams processing progress, live detections, and newly minted incidents over dedicated WebSockets (`/ws/analysis/{job_id}`).

### 5. Virtual Fencing & Behavior Rules
* **Multi-Point Polygon & Tripwire Zones**: User-configurable border sectors (`RESTRICTED`, `EXCLUSION`, `PATROL`, `MONITORING`).
* **Complex Movement Intelligence**:
  * Crossing direction detection (Inbound vs Outbound).
  * Loitering and stationary dwell-time monitoring.
  * Rapid movement / running trajectory alerts.
  * Abandoned object detection with temporal association.

### 6. BSA 2023 Section 63 Legal Evidence Vault
* **Court-Admissible Evidence**: Complies strictly with the **Bharatiya Sakshya Adhiniyam, 2023 — Section 63** (formerly Section 65B of the Indian Evidence Act).
* **Cryptographic Integrity**: SHA-256 hash sealing for every captured snapshot and MP4 video clip.
* **Tamper-Evident Manifests**: Cryptographic JSON manifests paired with downloadable, court-admissible PDF audit certificates.

### 7. C4ISR Tactical Command Center
* **Geospatial Map View**: Leaflet-powered GIS tactical map with BOP pins, camera sectors, real-time incident pins, and field assets.
* **Quick Reaction Team (QRT) Scramble**: Operator-initiated dispatch modal with tactical unit routing.
* **PTZ Camera Virtual Controller**: Preset patrols, digital pan/tilt/zoom adjustments, and tour schedules.
* **Tactical Audio HUD**: Real-time auditory alerts for breaches, intercept confirmations, and clicks.

---

## Quick Start Guide

### Prerequisites
* **Operating System**: macOS 12+ or Ubuntu 20.04/22.04 LTS
* **Python**: 3.9 to 3.11+
* **Node.js**: 18 LTS or 20 LTS

---

### Step 1: Clone Repository & Virtual Environment

```bash
# Clone repository
git clone https://github.com/VivekGitNinja/IBVAP.git
cd IBVAP

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

---

### Step 2: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

### Step 3: Run the Backend Service

```bash
# Start Uvicorn on Port 8001 (allows hardware camera capture)
.venv/bin/python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

* **Interactive OpenAPI Docs**: [http://localhost:8001/docs](http://localhost:8001/docs)
* **System Health Endpoint**: [http://localhost:8001/api/v1/status](http://localhost:8001/api/v1/status)

---

### Step 4: Run the Frontend Application

In a separate terminal window:

```bash
cd frontend
npm run dev
```

* **Command Center Dashboard**: [http://localhost:5173](http://localhost:5173)

---

## Default Operator Clearance Credentials

| Call Sign / Username | Password | Role Clearance | Capabilities |
| :--- | :--- | :--- | :--- |
| **`admin`** | `admin123` | `ADMIN` | Full configuration, user roles, system metrics |
| **`commander`** | `commander123` | `COMMANDER` | Threat escalation, QRT dispatch, zone modifications |
| **`operator`** | `operator123` | `OPERATOR` | Live monitoring, incident triage, ANPR/FRS scanning |

---

## Automated Verification & Test Suite

IBVAP features a comprehensive **188-test automated verification suite** validating core mathematical models, CV tracking, spatial geometry, security policies, FRS biometric matching, ANPR parsing, and chaos resilience:

```bash
# Execute full backend test suite
.venv/bin/pytest backend/tests/ -v
```

```
============================== 188 passed in 35.06s ==============================
- backend/tests/test_analysis_tracks.py ........ [PASS]
- backend/tests/test_anpr_night_face.py ........ [PASS]
- backend/tests/test_api.py .................... [PASS]
- backend/tests/test_audit.py .................. [PASS]
- backend/tests/test_c2_webhook.py ............. [PASS]
- backend/tests/test_chaos_resilience.py ....... [PASS]
- backend/tests/test_defense_upgrades.py ....... [PASS]
- backend/tests/test_evidence.py ............... [PASS]
- backend/tests/test_evidence_report.py ........ [PASS]
- backend/tests/test_geometry.py ............... [PASS]
- backend/tests/test_infrastructure.py ......... [PASS]
- backend/tests/test_live_sources.py ........... [PASS]
- backend/tests/test_observability.py .......... [PASS]
- backend/tests/test_ptz_and_nvr.py ............ [PASS]
- backend/tests/test_real_media_pipeline.py .... [PASS]
- backend/tests/test_scoring.py ................ [PASS]
- backend/tests/test_security.py ............... [PASS]
- backend/tests/test_system_integrity.py ....... [PASS]
- backend/tests/test_tracking.py ............... [PASS]
- backend/tests/test_zones.py .................. [PASS]
```

---

## End-to-End Visual Evidence Dossier

The platform includes **54 automated visual proof artifacts** generated during comprehensive E2E headless validation, located in `e2e/evidence/`:

* `01_login_page.png` — High-security operator authentication interface
* `03_login_success.png` — C4ISR tactical command dashboard with live feeds
* `04_nav_cameras.png` — Tactical camera matrix and status monitors
* `05_nav_media.png` — Offline surveillance video studio
* `06_nav_incidents.png` — Real-time threat queue and triage drawer
* `07_nav_evidence.png` — BSA Section 63 cryptographic evidence vault
* `08_nav_frs.png` — Biometric facial recognition suspect gallery
* `09_nav_map.png` — Geospatial tactical map with BOP sectors
* `26_zone_intrusion_incident.png` — Live perimeter breach detection
* `31_anpr_search_result.png` — Vehicle HSRP plate recognition & intercept
* `33_frs_watchlist_match_incident.png` — SFace biometric suspect match

---

## Key API Endpoints Summary

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/auth/token` | `POST` | Issues JWT token with role-based clearance |
| `/api/v1/cameras` | `GET / POST` | Real camera management & stream configuration |
| `/api/v1/cameras/{id}/snapshot` | `GET` | Live 1080p frame with real-time AI bounding boxes |
| `/api/v1/frs/watchlist` | `GET / POST` | Biometric suspect enrollment & embedding management |
| `/api/v1/frs/verify-probe` | `POST` | Forensic face photo verification against gallery |
| `/api/v1/anpr/plates` | `GET` | Logged vehicle license plate records & speeds |
| `/api/v1/anpr/scan` | `POST` | Manual ANPR scan & stolen vehicle intercept check |
| `/api/v1/anpr/scan-file` | `POST` | Photo OCR extraction & barrier trigger |
| `/api/v1/analysis/jobs` | `GET / POST` | Submits and monitors video file analysis jobs |
| `/api/v1/incidents` | `GET / POST` | Incident lifecycle (Acknowledge, Escalate, Dismiss) |
| `/api/v1/evidence/{id}` | `GET` | Cryptographic evidence details & SHA-256 validation |
| `/api/v1/evidence/{id}/pdf` | `GET` | Downloads court-admissible BSA 2023 Section 63 Certificate |
| `/ws/events` | `WebSocket` | Real-time tactical incident & telemetry event stream |

---

## Repository Structure

```
ibvap/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # REST APIs (Cameras, FRS, ANPR, Incidents, Evidence, Media)
│   │   ├── core/              # Military-grade security, JWT, and runtime settings
│   │   ├── db/                # SQLite database session and schema sync
│   │   ├── models/            # SQLAlchemy database entities (Incidents, Plates, FRS, Evidence)
│   │   └── services/          # Real AI pipelines (live_pipeline, video_analysis, anpr, face, c2)
│   ├── requirements.txt       # Python dependencies
│   └── tests/                 # 188 automated unit, API, and integration test suite
├── edge/
│   ├── detection/             # YOLO26n / YOLO11 neural detectors & factory
│   ├── modules/               # Night enhancement (Zero-DCE/CLAHE) & rules engines
│   ├── tracking/              # ByteTrack IoU centroid tracker
│   └── zones/                 # Virtual fence & polygon spatial intersection logic
├── frontend/
│   ├── src/
│   │   ├── components/        # Tactical HUD, TopBar, PTZ, GIS Map, WebSockets
│   │   ├── views/             # Live Monitor, FRS, ANPR Checkpost, Video Studio, Evidence
│   │   └── api.ts             # Type-safe client communication layer
│   └── package.json           # React 18, Vite, Lucide-React, Leaflet
├── models/                    # Pre-cached weights (YOLO26, YuNet, SFace)
├── scripts/                   # Model cache scripts & demo utilities
├── e2e/evidence/              # Visual proof verification dossiers (54 artifacts)
└── RUNBOOK.md                 # Complete field deployment and operational manual
```

---

## SIH 2026 Innovation Highlights (PS-26187)

1. **Air-Gap Native**: Fully functional without internet connectivity or external API calls.
2. **Explainable AI (XAI)**: Every threat score (0–100) is mathematically justified with visible reason codes.
3. **Legal Admissibility**: Built-in Section 63 Bharatiya Sakshya Adhiniyam compliance out of the box.
4. **Zero Synthetic Feeds**: Operates with authentic hardware video capture and real CCTV footage.
5. **Anti-Fatigue Deduplication**: Suppresses alarm floods while escalating verified high-threat breaches.
6. **Unified C4ISR Interface**: Fuses GIS mapping, biometric FRS, HSRP ANPR, and video analytics in a single tactical console.

---

## License & Evaluation Notice

This platform was built specifically for evaluation under **Smart India Hackathon 2026** (Problem Statement: **PS-26187**).  
All neural network weights are subject to their respective open-source licenses (Ultralytics, OpenCV Zoo).

*For field operation and deep deployment details, consult the [Operations Runbook](RUNBOOK.md).*
