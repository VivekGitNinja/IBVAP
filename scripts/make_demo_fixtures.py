#!/usr/bin/env python3
"""
IBVAP Demo Video Fixture Generator
====================================
SIH 2026 — PS-26187 | SSB MHA

Generates synthetic test videos in samples/ using pure OpenCV (no external assets needed).
These fixtures are used for:
  - CI/CD offline pipeline tests
  - Evaluator demonstrations
  - ANPR/face/zone crossing unit tests

Usage:
  python scripts/make_demo_fixtures.py [--output-dir samples] [--fps 10] [--width 640] [--height 480]

All videos are:
  - 640x480 pixels (PAL-equivalent)
  - 10 FPS (embedded in container)
  - MP4 (H.264 via OpenCV VideoWriter)
  - Synthetic / purely generated — NO real faces, plates, or identifiable data
"""

import argparse
import os
import math
import random
import sys

def _require_cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        print("ERROR: OpenCV not installed. Run: pip install opencv-python-headless", file=sys.stderr)
        sys.exit(1)

import numpy as np


def _writer(path, fps, w, h):
    cv2 = _require_cv2()
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))
    if not out.isOpened():
        raise RuntimeError(f"Failed to open VideoWriter for {path}")
    return out


def _draw_text(frame, text, pos, scale=0.5, color=(255, 255, 255)):
    cv2 = _require_cv2()
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1)


def _draw_grid(frame, step=40):
    """Draw a tactical grid for the background."""
    h, w = frame.shape[:2]
    for x in range(0, w, step):
        frame[:, x] = [20, 30, 20]
    for y in range(0, h, step):
        frame[y, :] = [20, 30, 20]


def make_day_crossing(output_dir, fps, w, h):
    """Synthetic daylight person crossing a virtual fence line."""
    cv2 = _require_cv2()
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "day_crossing.mp4")
    out = _writer(path, fps, w, h)

    fence_y = h // 2  # Horizontal fence line
    total_frames = fps * 8  # 8 seconds

    for frame_idx in range(total_frames):
        # Bright daylight background
        frame = np.full((h, w, 3), (180, 200, 180), dtype=np.uint8)
        _draw_grid(frame, step=60)

        # Fence line (red, dashed)
        for x in range(0, w, 20):
            if (x // 20) % 2 == 0:
                cv2.line(frame, (x, fence_y), (x + 16, fence_y), (0, 0, 200), 2)
        _draw_text(frame, "VIRTUAL FENCE LINE", (w // 2 - 100, fence_y - 10), color=(0, 0, 200))

        # Person silhouette moves top → bottom (crosses fence at frame 40)
        progress = frame_idx / total_frames
        person_y = int(30 + progress * (h - 80))
        person_x = w // 2

        # Body rectangle
        cv2.rectangle(frame, (person_x - 12, person_y), (person_x + 12, person_y + 40), (60, 100, 160), -1)
        # Head circle
        cv2.circle(frame, (person_x, person_y - 10), 12, (200, 170, 140), -1)

        if person_y > fence_y:
            _draw_text(frame, "! CROSSING DETECTED !", (w // 2 - 120, 30), color=(0, 0, 255))

        _draw_text(frame, "TEST FIXTURE", (w - 160, 20), scale=0.45, color=(0, 255, 255))
        _draw_text(frame, f"SECTOR ALPHA | DAYLIGHT | Frame {frame_idx + 1}/{total_frames}",
                   (10, 20), scale=0.4)
        out.write(frame)

    out.release()
    print(f"[OK] Generated: {path} ({total_frames} frames at {fps} FPS)")
    return path


def make_night_crossing(output_dir, fps, w, h):
    """Synthetic night-vision scene with low-light person movement."""
    cv2 = _require_cv2()
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "night_crossing.mp4")
    out = _writer(path, fps, w, h)

    total_frames = fps * 8  # 8 seconds
    rng = random.Random(42)  # Deterministic noise seed

    for frame_idx in range(total_frames):
        # Very dark background with noise (night camera simulation)
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Add grainy noise (poor-light sensor noise)
        noise = np.random.randint(0, 25, (h, w, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)

        # Faint IR-glow on ground (infrared illuminator)
        ir_intensity = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(ir_intensity, (w // 2, h - 10), (w // 3, h // 4), 0, 0, 360, 30, -1)
        frame[:, :, 2] = cv2.add(frame[:, :, 2], ir_intensity)  # IR shows in red channel

        # Person (bright in IR, slightly greenish)
        progress = frame_idx / total_frames
        person_y = int(30 + progress * (h - 80))
        person_x = w // 3

        cv2.rectangle(frame, (person_x - 10, person_y), (person_x + 10, person_y + 35),
                      (30, 200, 30), -1)  # Green for IR signature
        cv2.circle(frame, (person_x, person_y - 8), 10, (40, 220, 40), -1)

        # Night luminance label
        luminance = 12 + rng.randint(0, 6)
        _draw_text(frame, "TEST FIXTURE", (w - 160, 20), scale=0.45, color=(0, 255, 255))
        _draw_text(frame, f"NIGHT MODE | CLAHE ON | Lum={luminance} | Frame {frame_idx + 1}",
                   (10, 20), scale=0.4, color=(0, 220, 0))
        _draw_text(frame, "SECTOR BETA | IR ACTIVE", (w - 200, h - 10), scale=0.35, color=(0, 200, 0))

        out.write(frame)

    out.release()
    print(f"[OK] Generated: {path} ({total_frames} frames at {fps} FPS)")
    return path


def make_vehicle_plate(output_dir, fps, w, h):
    """Synthetic vehicle with rendered license plate for ANPR testing."""
    cv2 = _require_cv2()
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "vehicle_plate.mp4")
    out = _writer(path, fps, w, h)

    total_frames = fps * 6  # 6 seconds
    PLATE_TEXT = "DL 01 AB 1234"  # Synthetic plate (not a real vehicle)

    for frame_idx in range(total_frames):
        # Road background
        frame = np.full((h, w, 3), (80, 80, 80), dtype=np.uint8)
        # Road markings
        cv2.rectangle(frame, (0, h // 2), (w, h), (70, 70, 70), -1)
        for x in range(0, w, 60):
            cv2.rectangle(frame, (x, h // 2 + 20), (x + 40, h // 2 + 28), (255, 255, 200), -1)

        # Vehicle moves right to left
        progress = frame_idx / total_frames
        vx = int(w * 1.1 - progress * (w * 1.5))
        vy = h // 2 - 30

        # Vehicle body
        cv2.rectangle(frame, (vx, vy), (vx + 180, vy + 80), (50, 70, 150), -1)
        # Windshield
        cv2.rectangle(frame, (vx + 30, vy + 10), (vx + 150, vy + 40), (120, 150, 180), -1)
        # Wheels
        cv2.circle(frame, (vx + 35, vy + 80), 20, (30, 30, 30), -1)
        cv2.circle(frame, (vx + 145, vy + 80), 20, (30, 30, 30), -1)

        # License plate (high-contrast white rectangle + black text)
        plate_x = vx + 30
        plate_y = vy + 45
        plate_w = 125
        plate_h = 28
        cv2.rectangle(frame, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (255, 255, 255), -1)
        cv2.rectangle(frame, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (0, 0, 0), 2)
        cv2.putText(frame, PLATE_TEXT, (plate_x + 6, plate_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        _draw_text(frame, "TEST FIXTURE", (w - 160, 20), scale=0.45, color=(0, 255, 255))
        _draw_text(frame, f"ANPR ZONE | Frame {frame_idx + 1}/{total_frames}", (10, 20), scale=0.4)
        _draw_text(frame, f"PLATE: {PLATE_TEXT}", (10, h - 10), scale=0.45, color=(255, 255, 0))

        out.write(frame)

    out.release()
    print(f"[OK] Generated: {path} ({total_frames} frames at {fps} FPS)")
    return path


def make_loitering(output_dir, fps, w, h):
    """Synthetic person loitering (stationary for ~10 seconds) inside a zone."""
    cv2 = _require_cv2()
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "loitering.mp4")
    out = _writer(path, fps, w, h)

    total_frames = fps * 12  # 12 seconds
    rng = random.Random(99)
    zone_x, zone_y = w // 4, h // 4
    zone_w, zone_h = w // 2, h // 2

    for frame_idx in range(total_frames):
        frame = np.full((h, w, 3), (160, 180, 160), dtype=np.uint8)
        _draw_grid(frame, step=50)

        # Zone polygon (monitoring area)
        cv2.rectangle(frame, (zone_x, zone_y), (zone_x + zone_w, zone_y + zone_h),
                      (0, 180, 255), 2)
        _draw_text(frame, "MONITORING ZONE", (zone_x + 10, zone_y + 20),
                    color=(0, 180, 255))

        # Person: stays roughly in center with micro-jitter (loitering simulation)
        px = w // 2 + rng.randint(-5, 5)
        py = h // 2 + rng.randint(-3, 3)

        cv2.rectangle(frame, (px - 12, py - 35), (px + 12, py + 5), (60, 100, 160), -1)
        cv2.circle(frame, (px, py - 45), 12, (200, 170, 140), -1)

        dwell = frame_idx / fps
        color = (0, 200, 0) if dwell < 10 else (0, 0, 255)
        _draw_text(frame, "TEST FIXTURE", (w - 160, 20), scale=0.45, color=(0, 255, 255))
        _draw_text(frame, f"DWELL: {dwell:.1f}s", (10, 50), scale=0.6, color=color)
        if dwell >= 10:
            _draw_text(frame, "! LOITERING ALERT !", (w // 2 - 120, 30), color=(0, 0, 255))
        _draw_text(frame, f"SECTOR GAMMA | Frame {frame_idx + 1}/{total_frames}",
                   (10, 20), scale=0.4)

        out.write(frame)

    out.release()
    print(f"[OK] Generated: {path} ({total_frames} frames at {fps} FPS)")
    return path


def make_readme(output_dir):
    readme_path = os.path.join(output_dir, "README.md")
    content = """\
# IBVAP Sample Video Fixtures
## SIH 2026 — PS-26187 | SSB MHA

These videos are **fully synthetic** — generated by `scripts/make_demo_fixtures.py`
using pure OpenCV. They contain NO real faces, real license plates, or identifiable
personal data. They exist solely for testing and evaluation.

---

| File | Duration | Description | Primary Test |
|------|----------|-------------|--------------|
| `day_crossing.mp4` | 8s | Person crossing a virtual fence in daylight | Zone crossing detection |
| `night_crossing.mp4` | 8s | Night scene with IR signature and CLAHE | Night luminance + CLAHE |
| `vehicle_plate.mp4` | 6s | Vehicle with synthetic license plate (DL 01 AB 1234) | ANPR pipeline |
| `loitering.mp4` | 12s | Person stationary inside monitoring zone >10s | Loitering rule |

---

## Regenerating Fixtures

```bash
python scripts/make_demo_fixtures.py
```

## Uploading for Analysis

```bash
curl -X POST http://localhost:8001/api/v1/jobs \\
  -F "file=@samples/day_crossing.mp4" \\
  -F "camera_id=1"
```

---

*Fixtures are deterministic (seeded RNG). Re-generation produces identical files.*
"""
    with open(readme_path, "w") as f:
        f.write(content)
    print(f"[OK] Generated: {readme_path}")


def main():
    parser = argparse.ArgumentParser(description="IBVAP Demo Fixture Generator")
    parser.add_argument("--output-dir", default="samples", help="Output directory")
    parser.add_argument("--fps", type=int, default=10, help="Frames per second")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    args = parser.parse_args()

    cv2 = _require_cv2()
    import numpy  # Ensure numpy is available

    print(f"IBVAP Demo Fixture Generator — SIH 2026")
    print(f"Output dir : {os.path.abspath(args.output_dir)}")
    print(f"Resolution : {args.width}x{args.height} @ {args.fps} FPS")
    print()

    make_day_crossing(args.output_dir, args.fps, args.width, args.height)
    make_night_crossing(args.output_dir, args.fps, args.width, args.height)
    make_vehicle_plate(args.output_dir, args.fps, args.width, args.height)
    make_loitering(args.output_dir, args.fps, args.width, args.height)
    make_readme(args.output_dir)

    print()
    print("All fixtures generated successfully.")
    print(f"See {args.output_dir}/README.md for details.")


if __name__ == "__main__":
    main()
