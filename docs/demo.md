# IBVAP Demo Guide

## Quick Demo (5 minutes)

### Step 1: Start the System
```bash
# Backend
PYTHONPATH=. uvicorn backend.app.main:app --reload

# Frontend
cd frontend && npm run dev
```

### Step 2: Open Dashboard
Navigate to http://localhost:5173

### Step 3: Run Demo Scenario
Click "▶ Run Intrusion Demo" on the dashboard.

### Step 4: Show the Incident
- Point to the incident card showing CRITICAL severity
- Show the threat score (85+/100)
- Show the reason codes

### Step 5: Open Incident Detail
Click on the incident card. Show:
- AI Assessment panel (what was detected, confidence, behavior)
- Signal Contributions (visual bar chart of scoring signals)
- Recommended Action
- Timeline (chronological events)
- Evidence (SHA-256 hash)

### Step 6: Verify Evidence
Click "🔒 Verify Integrity" to show SHA-256 verification.

### Step 7: Acknowledge Incident
Click "✓ ACKNOWLEDGE" to demonstrate human-in-the-loop.

### Step 8: Show Other Pages
- Camera Health page
- Audit Trail page
- Demo Center page (all 6 scenarios)

## SIH Presentation Script (5-7 minutes)

### 00:00 - Problem Statement
"We solve AI-based border surveillance for SSB using existing CCTV."

### 00:30 - Dashboard Overview
Show: cameras online, incidents, alerts, system status.

### 01:00 - Live Camera Grid
Show camera health status, BOP locations.

### 01:30 - Intrusion Detection
Run intrusion demo. Show the detection → zone crossing → scoring pipeline.

### 02:00 - AI Reasoning
Open incident detail. Show:
- What was detected (person-like object)
- Where (restricted zone)
- Why the score increased (contributions)

### 02:30 - Threat Score Explanation
Show the signal contributions chart. Explain each signal.

### 03:00 - Alert & Evidence
Show alert generation. Verify evidence integrity.

### 03:30 - Human Verification
Acknowledge the incident. Show timeline updates.

### 04:00 - Other Scenarios
Quickly run: Night Movement, Loitering, Multi-Camera.

### 04:30 - Camera Health
Show camera health dashboard with different states.

### 05:00 - Architecture
Show the pipeline visualization. Explain edge-first design.

### 05:30 - Key Innovations
1. Explainable Threat Scoring
2. Offline-First Store-and-Forward
3. Human-in-the-Loop Verification
4. Tamper-Evident Evidence

### 06:00 - Impact & Scalability
Explain how 1 camera → 100 cameras works.

### 06:30 - Thank You
Show the innovation points list.

## Available Scenarios

| Scenario | Severity | What It Shows |
|----------|----------|---------------|
| Intrusion | CRITICAL | Zone crossing + loitering + scoring |
| Night Movement | HIGH | Night context weighting |
| Loitering | MEDIUM | Extended dwell detection |
| Vehicle | HIGH | Vehicle near restricted zone |
| Abandoned Object | HIGH | Stationary object detection |
| Multi-Camera | CRITICAL | Cross-camera correlation |
