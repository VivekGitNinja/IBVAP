#!/usr/bin/env python3
"""Offline model cache verification and asset preparation script.

Ensures all computer vision weights and models are available offline in models/
with zero runtime network dependencies during operational inference.
"""

import os
import sys
import glob
from pathlib import Path
import urllib.request

MODELS_DIR = Path("models")


def check_or_fetch(filename: str, url: str, description: str):
    target = MODELS_DIR / filename
    if target.exists() and target.stat().st_size > 1000:
        print(f"  [CACHED]     {description:<25} -> {target} ({target.stat().st_size / 1024 / 1024:.1f} MB)")
        return True

    print(f"  [DOWNLOADING] {description:<25} from {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response, open(target, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"  [SUCCESS]    Cached {filename} ({target.stat().st_size / 1024 / 1024:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [OFFLINE]    Could not download {filename} ({e}). Local fallback will be used.")
        return False


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print("\n======================================================================")
    print("      IBVAP OFFLINE MODEL CACHE PREPARATION & VERIFICATION            ")
    print("======================================================================\n")

    # 1. Inspect existing YOLO weights
    yolo_weights = list(MODELS_DIR.glob("yolo*.onnx")) + list(MODELS_DIR.glob("yolo*.pt"))
    if yolo_weights:
        for w in yolo_weights:
            print(f"  [CACHED]     YOLO Detector Model       -> {w.name} ({w.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print("  [MISSING]    No YOLO weights found in models/. Using OpenCV MOG2 fallback.")

    # 2. YuNet Face Model
    check_or_fetch(
        "face_detection_yunet_2023mar.onnx",
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "OpenCV YuNet Face Detector",
    )

    print("\n----------------------------------------------------------------------")
    print(f"  Offline Cache Status: {len(list(MODELS_DIR.glob('*')))} files in {MODELS_DIR}/")
    print("  Zero Runtime Downloads Policy: Active.")
    print("======================================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
