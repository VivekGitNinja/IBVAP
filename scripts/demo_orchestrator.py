#!/usr/bin/env python3
"""
IBVAP Demo Orchestrator — SIH 2026 Judge Demonstration
======================================================

Runs a complete 5-minute demonstration of all IBVAP capabilities.
This script is designed for the SIH 2026 hackathon presentation.

Demo Flow:
00:00 — System starts, cameras connect
00:30 — Live YOLO26n detection on video
01:00 — Person crosses restricted zone (loitering alert)
01:30 — Night movement detected
02:00 — Vehicle ANPR candidate generated
02:30 — Multi-camera correlation triggered
03:00 — Abandoned object detected
03:30 — Evidence captured with SHA-256 hash
04:00 — Incident timeline displayed
04:30 — Offline mode simulated
05:00 — Dashboard summary

Usage:
    python scripts/demo_orchestrator.py

Requirements:
    - Backend running on http://localhost:8080
    - Sample video file (auto-downloads if not present)
"""

import os
import sys
import json
import time
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("demo")

BASE_URL = "http://localhost:8080"
SAMPLE_VIDEO_URL = "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
SAMPLE_VIDEO_PATH = "/tmp/ibvap_demo_video.mp4"


def check_backend():
    """Verify backend is running."""
    try:
        r = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if r.status_code == 200:
            logger.info("✅ Backend is running")
            return True
    except Exception:
        pass
    
    logger.error("❌ Backend not running. Start with:")
    logger.error("   cd ~/Downloads/ibvap && source .venv/bin/activate")
    logger.error("   PYTHONPATH=. uvicorn backend.app.main:app --host 127.0.0.1 --port 8080")
    return False


def download_sample_video():
    """Download a sample video if not present."""
    if os.path.exists(SAMPLE_VIDEO_PATH):
        logger.info(f"✅ Sample video exists: {SAMPLE_VIDEO_PATH}")
        return True
    
    logger.info("📥 Downloading sample video...")
    try:
        r = requests.get(SAMPLE_VIDEO_URL, stream=True, timeout=30)
        with open(SAMPLE_VIDEO_PATH, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"✅ Downloaded: {SAMPLE_VIDEO_PATH}")
        return True
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return False


def register_demo_cameras():
    """Register sample cameras for the demo."""
    cameras = [
        {
            "name": "BOP-01 Gate Camera",
            "stream_url": f"file://{SAMPLE_VIDEO_PATH}",
            "location": "Border Outpost 01 — Main Gate",
            "bop": "BOP-01",
            "camera_type": "FILE"
        },
        {
            "name": "BOP-01 Perimeter Camera",
            "stream_url": f"file://{SAMPLE_VIDEO_PATH}",
            "location": "Border Outpost 01 — Perimeter",
            "bop": "BOP-01",
            "camera_type": "FILE"
        },
        {
            "name": "BOP-02 Watchtower Camera",
            "stream_url": f"file://{SAMPLE_VIDEO_PATH}",
            "location": "Border Outpost 02 — Watchtower",
            "bop": "BOP-02",
            "camera_type": "FILE"
        },
    ]
    
    registered = []
    for cam in cameras:
        try:
            r = requests.post(f"{BASE_URL}/api/v1/cameras", json=cam, timeout=10)
            if r.status_code in (200, 201):
                data = r.json()
                cam_id = data.get("id", "unknown")
                registered.append(cam_id)
                logger.info(f"✅ Camera registered: {cam['name']} (ID: {cam_id})")
            else:
                logger.warning(f"⚠️ Camera registration returned {r.status_code}")
        except Exception as e:
            logger.error(f"❌ Camera registration failed: {e}")
    
    return registered


def create_zones(camera_id: str):
    """Create demo zones for a camera."""
    zones = [
        {
            "camera_id": camera_id,
            "name": "Restricted Perimeter",
            "type": "restricted",
            "polygon": [[100, 100], [500, 100], [500, 400], [100, 400]],
            "severity": "CRITICAL"
        },
        {
            "camera_id": camera_id,
            "name": "Monitoring Zone",
            "type": "monitoring",
            "polygon": [[50, 50], [600, 50], [600, 450], [50, 450]],
            "severity": "MEDIUM"
        },
        {
            "camera_id": camera_id,
            "name": "Patrol Route",
            "type": "patrol",
            "polygon": [[0, 0], [700, 0], [700, 500], [0, 500]],
            "severity": "LOW"
        },
    ]
    
    for zone in zones:
        try:
            r = requests.post(f"{BASE_URL}/api/v1/zones", json=zone, timeout=10)
            if r.status_code in (200, 201):
                logger.info(f"✅ Zone created: {zone['name']}")
        except Exception as e:
            logger.warning(f"⚠️ Zone creation failed: {e}")


def run_demo_scenario(scenario_name: str):
    """Run a specific demo scenario."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🎬 RUNNING SCENARIO: {scenario_name.upper()}")
    logger.info(f"{'='*60}")
    
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/demo/seed/{scenario_name}",
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            incident_id = data.get("incident_id", "unknown")
            score = data.get("threat_score", 0)
            severity = data.get("severity", "UNKNOWN")
            logger.info(f"✅ Scenario created incident: {incident_id}")
            logger.info(f"   Threat Score: {score} | Severity: {severity}")
            return data
        else:
            logger.error(f"❌ Scenario failed: {r.status_code} — {r.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"❌ Scenario error: {e}")
        return None


def verify_data():
    """Verify that demo data was created correctly."""
    logger.info(f"\n{'='*60}")
    logger.info("📊 VERIFYING DEMO DATA")
    logger.info(f"{'='*60}")
    
    checks = [
        ("/api/v1/cameras", "Cameras"),
        ("/api/v1/incidents", "Incidents"),
        ("/api/v1/alerts", "Alerts"),
        ("/api/v1/evidence", "Evidence"),
    ]
    
    all_ok = True
    for endpoint, name in checks:
        try:
            r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                count = len(data) if isinstance(data, list) else data.get("count", "?")
                logger.info(f"✅ {name}: {count} records")
            else:
                logger.error(f"❌ {name}: HTTP {r.status_code}")
                all_ok = False
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            all_ok = False
    
    # Check incident detail
    try:
        r = requests.get(f"{BASE_URL}/api/v1/incidents", timeout=10)
        incidents = r.json()
        if incidents:
            inc = incidents[0]
            inc_id = inc.get("id", "?")
            r2 = requests.get(f"{BASE_URL}/api/v1/incidents/{inc_id}", timeout=10)
            if r2.status_code == 200:
                detail = r2.json()
                has_timeline = len(detail.get("timeline", [])) > 0
                has_evidence = len(detail.get("evidence", [])) > 0
                has_score = detail.get("threat_score", 0) > 0
                logger.info(f"✅ Incident detail: timeline={has_timeline}, evidence={has_evidence}, score={has_score}")
            else:
                logger.error(f"❌ Incident detail: HTTP {r2.status_code}")
                all_ok = False
    except Exception as e:
        logger.error(f"❌ Incident detail check: {e}")
        all_ok = False
    
    return all_ok


def run_full_demo():
    """Run the complete SIH demo sequence."""
    start_time = time.time()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║            IBVAP — SIH 2026 DEMO ORCHESTRATOR              ║
║    Intelligent Border Video Analytics Platform              ║
║    Ministry of Home Affairs / SSB                           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Check backend
    logger.info("STEP 1/8: Checking backend...")
    if not check_backend():
        return False
    
    # Step 2: Download sample video
    logger.info("\nSTEP 2/8: Preparing sample video...")
    if not download_sample_video():
        logger.warning("⚠️ No sample video — using demo:// cameras only")
    
    # Step 3: Register cameras
    logger.info("\nSTEP 3/8: Registering cameras...")
    cameras = register_demo_cameras()
    
    # Step 4: Create zones for first camera
    if cameras:
        logger.info("\nSTEP 4/8: Creating surveillance zones...")
        create_zones(cameras[0])
    
    # Step 5: Run demo scenarios
    logger.info("\nSTEP 5/8: Running demo scenarios...")
    scenarios = [
        "intrusion",       # Restricted zone intrusion
        "night_movement",  # Night-time movement
        "loitering",       # Extended loitering
        "vehicle_anpr",    # Vehicle near restricted zone
        "abandoned",       # Abandoned object
        "multicamera",     # Multi-camera correlation
    ]
    
    results = []
    for scenario in scenarios:
        result = run_demo_scenario(scenario)
        if result:
            results.append(result)
        time.sleep(0.5)  # Brief pause between scenarios
    
    # Step 6: Start live pipeline on first camera
    if cameras:
        logger.info(f"\nSTEP 6/8: Starting live pipeline on camera {cameras[0]}...")
        try:
            r = requests.post(
                f"{BASE_URL}/api/v1/cameras/{cameras[0]}/pipeline/start",
                timeout=10
            )
            if r.status_code == 200:
                logger.info("✅ Live pipeline started")
            else:
                logger.warning(f"⚠️ Pipeline start returned {r.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Pipeline start failed: {e}")
    
    # Step 7: Wait for pipeline to process
    logger.info("\nSTEP 7/8: Waiting for live detection...")
    time.sleep(5)
    
    # Step 8: Verify everything
    logger.info("\nSTEP 8/8: Verifying demo data...")
    all_ok = verify_data()
    
    # Summary
    elapsed = time.time() - start_time
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    DEMO COMPLETE                            ║
╠══════════════════════════════════════════════════════════════╣
║  Time:        {elapsed:.1f}s                                     ║
║  Scenarios:   {len(results)}/{len(scenarios)} completed                              ║
║  Cameras:     {len(cameras)} registered                                  ║
║  Status:      {'ALL CHECKS PASSED ✅' if all_ok else 'SOME CHECKS FAILED ⚠️':<40}║
║                                                              ║
║  Open dashboard: http://localhost:8080                       ║
║                                                              ║
║  IBVAP — Ready for SIH 2026 presentation!                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Save results
    results_file = Path("/tmp/ibvap_demo_results.json")
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            "scenarios_run": len(results),
            "scenarios_total": len(scenarios),
            "cameras_registered": len(cameras),
            "all_checks_passed": all_ok,
            "results": results,
        }, f, indent=2, default=str)
    
    logger.info(f"📄 Results saved to {results_file}")
    
    return all_ok


if __name__ == "__main__":
    success = run_full_demo()
    sys.exit(0 if success else 1)
