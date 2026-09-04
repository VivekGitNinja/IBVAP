#!/usr/bin/env python3
"""
IBVAP Installation Verifier
============================

Checks that all required components are installed and working.
Run before demo to verify everything is ready.

Usage:
    python scripts/verify_installation.py
"""

import sys
import os
import importlib
from pathlib import Path

# Color codes
PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"
INFO = "\033[94mℹ️  INFO\033[0m"

results = {"pass": 0, "fail": 0, "warn": 0}


def check(name: str, condition: bool, detail: str = "", severity: str = "pass"):
    """Print a check result."""
    if condition:
        print(f"  {PASS} {name}")
        if detail:
            print(f"       {INFO} {detail}")
        results["pass"] += 1
    elif severity == "warn":
        print(f"  {WARN} {name}")
        if detail:
            print(f"       {INFO} {detail}")
        results["warn"] += 1
    else:
        print(f"  {FAIL} {name}")
        if detail:
            print(f"       {INFO} {detail}")
        results["fail"] += 1


def main():
    print("=" * 60)
    print("  IBVAP Installation Verification")
    print("=" * 60)
    print()

    # ── Python Version ──
    print("Python Environment:")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    check(f"Python {py_ver}", sys.version_info >= (3, 9), f"Path: {sys.executable}")

    # ── Core Dependencies ──
    print("\nCore Dependencies:")
    deps = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("sqlalchemy", "Database ORM"),
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("jwt", "PyJWT"),
    ]
    for module_name, desc in deps:
        try:
            mod = importlib.import_module(module_name)
            ver = getattr(mod, "__version__", "installed")
            check(f"{desc} ({module_name})", True, f"Version: {ver}")
        except ImportError:
            check(f"{desc} ({module_name})", False, f"Not installed: pip install {module_name}")

    # ── AI Dependencies ──
    print("\nAI/ML Dependencies:")
    try:
        import ultralytics
        check("Ultralytics YOLO", True, f"Version: {ultralytics.__version__}")
    except ImportError:
        check("Ultralytics YOLO", False, "pip install ultralytics")

    try:
        import onnxruntime
        check("ONNX Runtime", True, f"Version: {onnxruntime.__version__}")
    except ImportError:
        check("ONNX Runtime", False, "pip install onnxruntime (optional)")

    try:
        import insightface
        check("InsightFace", True, "Face detection + embedding")
    except ImportError:
        check("InsightFace", False, "pip install insightface (optional)", severity="warn")

    # ── Edge Modules ──
    print("\nEdge Modules:")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    modules = [
        ("edge.detection.factory", "Detector Factory"),
        ("edge.detection.yolo26", "YOLO26 Detector"),
        ("edge.detection.yolo11", "YOLO11 Detector"),
        ("edge.detection.motion", "Motion Detector"),
        ("edge.detection.anpr", "ANPR Pipeline"),
        ("edge.detection.face_detector", "Face Detector"),
        ("edge.tracking.bytetrack", "ByteTrack Tracker"),
        ("edge.tracking.centroid", "Centroid Tracker"),
        ("edge.modules.face_recognition", "Face Recognition"),
        ("edge.modules.reid", "Re-ID Engine"),
        ("edge.modules.activity_rules", "Activity Rules"),
        ("edge.modules.night_enhance", "Night Enhancer"),
    ]
    for module_path, desc in modules:
        try:
            importlib.import_module(module_path)
            check(f"{desc}", True)
        except Exception as e:
            check(f"{desc}", False, str(e)[:80])

    # ── Backend Services ──
    print("\nBackend Services:")
    services = [
        ("backend.app.services.scoring", "Threat Scoring"),
        ("backend.app.services.evidence", "Evidence Engine"),
        ("backend.app.services.correlation", "Correlation Engine"),
        ("backend.app.services.offline_queue", "Offline Queue"),
        ("backend.app.services.live_pipeline", "Live Pipeline"),
    ]
    for module_path, desc in services:
        try:
            importlib.import_module(module_path)
            check(f"{desc}", True)
        except Exception as e:
            check(f"{desc}", False, str(e)[:80])

    # ── Database ──
    print("\nDatabase:")
    db_path = Path(__file__).resolve().parent.parent / "ibvap.db"
    check("SQLite database", db_path.exists(), f"Path: {db_path}", severity="warn")

    # ── Models ──
    print("\nAI Models:")
    model_paths = [
        (["models/yolo26n.pt", "yolo26n.pt"], "YOLO26n model"),
        (["models/yolo11n.onnx", "yolo11n.pt", "models/yolo11n.pt"], "YOLO11n model"),
    ]
    for paths, desc in model_paths:
        full_paths = [Path(__file__).resolve().parent.parent / p for p in paths]
        exists = any(fp.exists() for fp in full_paths)
        found_path = next((fp for fp in full_paths if fp.exists()), full_paths[0])
        check(f"{desc}", exists, f"Path: {found_path}", severity="warn")

    # ── Frontend ──
    print("\nFrontend:")
    dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    check("Frontend build", dist.exists() and (dist / "index.html").exists(),
          f"Path: {dist}", severity="warn")

    # ── Summary ──
    print()
    print("=" * 60)
    total = results["pass"] + results["fail"] + results["warn"]
    print(f"  Results: {results['pass']} PASS / {results['fail']} FAIL / {results['warn']} WARN  (of {total} checks)")

    if results["fail"] == 0:
        print(f"  {PASS} Installation verified — ready for demo!")
    else:
        print(f"  {FAIL} {results['fail']} critical failures — fix before demo")
    print("=" * 60)

    return results["fail"]


if __name__ == "__main__":
    sys.exit(main())
