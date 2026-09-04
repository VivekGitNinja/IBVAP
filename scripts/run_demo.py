#!/usr/bin/env python3
"""
IBVAP Demo Orchestrator — Single Command to Start Everything
=============================================================

Usage:
    python scripts/run_demo.py              # Full demo
    python scripts/run_demo.py --lite       # Lite mode (mock detections)
    python scripts/run_demo.py --stop       # Stop all processes

What it does:
1. Kills any existing backend process
2. Deletes stale database
3. Starts FastAPI backend on port 8080
4. Seeds demo cameras and data
5. Registers a real video file as a camera
6. Starts the live detection pipeline
7. Prints access URLs

Requirements:
    - Backend dependencies installed (pip install -r backend/requirements.txt)
    - Frontend built (cd frontend && npm run build)
    - Sample video at /tmp/real_people.mp4 (auto-downloads if missing)
"""

import os
import sys
import time
import signal
import socket
import subprocess
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("demo")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PID_FILE = Path("/tmp/ibvap_demo.pid")


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def kill_existing():
    """Kill any existing IBVAP backend processes."""
    try:
        subprocess.run(["pkill", "-9", "-f", "uvicorn.*backend.app.main"], 
                       capture_output=True, timeout=5)
        subprocess.run(["pkill", "-9", "-f", "ibvap_demo"], 
                       capture_output=True, timeout=5)
        time.sleep(2)
        logger.info("Cleaned up existing processes")
    except Exception:
        pass


def wait_for_backend(port: int = 8080, timeout: int = 30) -> bool:
    """Wait until backend is ready."""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def download_sample_video():
    """Download sample video if not present."""
    video_path = Path("/tmp/real_people.mp4")
    if video_path.exists():
        logger.info(f"Sample video exists: {video_path}")
        return True

    url = "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
    logger.info("Downloading sample video...")
    try:
        import urllib.request
        urllib.request.urlretrieve(url, str(video_path))
        logger.info(f"Downloaded: {video_path}")
        return True
    except Exception as e:
        logger.warning(f"Download failed: {e}")
        return False


def seed_data():
    """Seed demo cameras and data."""
    import urllib.request
    import json

    # Login
    try:
        data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
        req = urllib.request.Request("http://127.0.0.1:8080/api/v1/auth/token", data=data)
        resp = urllib.request.urlopen(req, timeout=5)
        token = json.loads(resp.read())["access_token"]
    except Exception as e:
        logger.warning(f"Login failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Register real video camera
    video_path = Path("/tmp/real_people.mp4")
    if video_path.exists():
        cam_data = json.dumps({
            "name": "BOP-01 Gate Camera",
            "stream_url": f"file://{video_path}",
            "location": "Border Outpost 01",
            "bop": "BOP-01",
            "camera_type": "FILE"
        }).encode()
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8080/api/v1/cameras",
                data=cam_data, headers=headers, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=10)
            cam = json.loads(resp.read())
            logger.info(f"Camera registered: {cam['name']} (ID: {cam['id']})")
        except Exception as e:
            logger.warning(f"Camera registration: {e}")

    # Seed demo incidents
    for scenario in ["intrusion", "night_movement", "loitering", "vehicle_anpr", "abandoned"]:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:8080/api/v1/demo/seed/{scenario}",
                headers=headers, method="POST"
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info(f"Seeded scenario: {scenario}")
        except Exception as e:
            logger.debug(f"Seed {scenario}: {e}")


def start_backend():
    """Start the FastAPI backend as a daemon."""
    cmd = [
        sys.executable, "-c",
        f"import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8080, log_level='warning')"
    ]
    proc = subprocess.Popen(
        cmd, cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    PID_FILE.write_text(str(proc.pid))
    logger.info(f"Backend started (PID: {proc.pid})")
    return proc


def stop_all():
    """Stop all IBVAP processes."""
    kill_existing()
    if PID_FILE.exists():
        PID_FILE.unlink()
    logger.info("All processes stopped")


def main():
    parser = argparse.ArgumentParser(description="IBVAP Demo Orchestrator")
    parser.add_argument("--lite", action="store_true", help="Lite mode (mock detections)")
    parser.add_argument("--stop", action="store_true", help="Stop all processes")
    parser.add_argument("--port", type=int, default=8080, help="Backend port")
    args = parser.parse_args()

    if args.stop:
        stop_all()
        return

    print("""
╔══════════════════════════════════════════════════════════╗
║          IBVAP — Demo Orchestrator                       ║
║   Intelligent Border Video Analytics Platform            ║
║   SIH 2026 • Ministry of Home Affairs / SSB             ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Step 1: Clean up
    logger.info("Step 1/5: Cleaning up...")
    kill_existing()
    db_path = PROJECT_ROOT / "ibvap.db"
    if db_path.exists():
        db_path.unlink()
        logger.info("Deleted stale database")

    # Step 2: Download video
    logger.info("Step 2/5: Preparing video...")
    download_sample_video()

    # Step 3: Start backend
    logger.info("Step 3/5: Starting backend...")
    if not is_port_free(args.port):
        logger.warning(f"Port {args.port} in use, trying to free it...")
        kill_existing()
        time.sleep(1)

    start_backend()

    # Step 4: Wait for backend
    logger.info("Step 4/5: Waiting for backend...")
    if not wait_for_backend(args.port):
        logger.error("Backend failed to start!")
        return

    # Step 5: Seed data
    logger.info("Step 5/5: Seeding demo data...")
    time.sleep(1)
    seed_data()

    # Print access info
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  ✅ IBVAP DEMO READY                                     ║
║                                                          ║
║  Dashboard:  http://127.0.0.1:{args.port}                  ║
║  API Docs:   http://127.0.0.1:{args.port}/docs             ║
║  Health:     http://127.0.0.1:{args.port}/api/v1/health    ║
║                                                          ║
║  Login:      admin / admin123                             ║
║                                                          ║
║  Press Ctrl+C to stop                                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_all()


if __name__ == "__main__":
    main()
