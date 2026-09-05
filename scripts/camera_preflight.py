#!/usr/bin/env python3
"""
Camera permission and device preflight check for IBVAP.
Tests camera indices 0, 1, 2 on macOS using AVFoundation.
Prints resolution, FPS, and 5-frame average brightness.
"""

import sys
import time
import numpy as np
import cv2

def test_camera_index(idx: int):
    backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
    print(f"--- Testing Camera Index {idx} (backend={backend}) ---")
    cap = cv2.VideoCapture(idx, backend)
    if not cap.isOpened():
        print(f"Index {idx}: Unable to open device.")
        return None

    # Wait briefly for sensor warm-up
    time.sleep(0.5)

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    frames = []
    brightnesses = []

    for i in range(5):
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"Index {idx}, Frame {i+1}: Failed to read frame.")
            break
        frames.append(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        brightnesses.append(brightness)
        print(f"Index {idx}, Frame {i+1}: Read {frame.shape[1]}x{frame.shape[0]}, mean brightness={brightness:.2f}")
        time.sleep(0.1)

    cap.release()

    if len(frames) == 5:
        avg_brightness = float(np.mean(brightnesses))
        print(f"Index {idx} SUCCESS: 5/5 frames captured. Resolution: {int(width)}x{int(height)}, Reported FPS: {fps}, Avg Brightness: {avg_brightness:.2f}")
        return {
            "index": idx,
            "width": int(width),
            "height": int(height),
            "fps": fps,
            "avg_brightness": avg_brightness,
            "frames_captured": len(frames)
        }
    else:
        print(f"Index {idx} FAILED: Only {len(frames)}/5 frames captured.")
        return None

def main():
    print(f"Host OS: {sys.platform}")
    results = []
    for idx in range(3):
        res = test_camera_index(idx)
        if res:
            results.append(res)

    print("\n================ PREFLIGHT SUMMARY ================")
    if not results:
        print("ERROR: No camera devices could be opened or returned frames.")
        print("On macOS, ensure Terminal/IDE has Camera access in:")
        print("System Settings -> Privacy & Security -> Camera")
        sys.exit(1)

    print(f"Discovered {len(results)} active camera device(s):")
    for r in results:
        print(f"  - Camera Index {r['index']}: {r['width']}x{r['height']} @ {r['fps']} FPS, Avg Brightness: {r['avg_brightness']:.1f}")

    # Pick index with positive brightness (not pitch black / virtual dead device)
    valid = [r for r in results if r['avg_brightness'] > 5.0]
    if valid:
        primary = valid[0]
        print(f"\nRecommended Primary Webcam: Index {primary['index']} ({primary['width']}x{primary['height']})")
    else:
        primary = results[0]
        print(f"\nWarning: All cameras have very low brightness. Using Index {primary['index']}")

    return primary['index']

if __name__ == "__main__":
    main()
