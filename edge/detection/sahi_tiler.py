"""
SAHI (Slicing Aided Hyper Inference) Watchtower Tiler
=====================================================
Performs overlapping tile-based inference for long-range border surveillance.

Problem:
Watchtower cameras (mounted 20-30m high) monitor international borders across 1 to 3 km.
At that distance, a crawling infiltrator or moving vehicle occupies only 12x12 to 24x24 pixels.
Standard 640x640 detectors downsample high-resolution feeds (1080p/4K), losing distant targets.

Solution:
1. Slices high-resolution frame into overlapping windows (default 640x640 with 20% overlap).
2. Runs detector on each tile at native resolution.
3. Translates bounding boxes from tile coordinates to global frame coordinates.
4. Merges overlapping detections using global Non-Maximum Suppression (NMS).
"""

from __future__ import annotations
from typing import List, Tuple
import cv2
import numpy as np

from edge.detection.base import Detection, Detector


def slice_frame(
    frame: np.ndarray,
    slice_width: int = 640,
    slice_height: int = 640,
    overlap_ratio: float = 0.2,
) -> List[Tuple[np.ndarray, int, int]]:
    """Slice an image into overlapping tiles.

    Returns:
        List of tuples: (tile_image, global_x_offset, global_y_offset)
    """
    h, w = frame.shape[:2]
    step_x = int(slice_width * (1.0 - overlap_ratio))
    step_y = int(slice_height * (1.0 - overlap_ratio))

    tiles = []
    y = 0
    while y < h:
        x = 0
        y_end = min(y + slice_height, h)
        y_start = max(0, y_end - slice_height)

        while x < w:
            x_end = min(x + slice_width, w)
            x_start = max(0, x_end - slice_width)

            tile = frame[y_start:y_end, x_start:x_end]
            tiles.append((tile, x_start, y_start))

            if x_end >= w:
                break
            x += step_x

        if y_end >= h:
            break
        y += step_y

    return tiles


def run_sahi_inference(
    detector: Detector,
    frame: np.ndarray,
    frame_id: int = 0,
    slice_width: int = 640,
    slice_height: int = 640,
    overlap_ratio: float = 0.2,
    nms_iou_threshold: float = 0.45,
) -> List[Detection]:
    """Execute SAHI sliced inference on a high-resolution frame.

    Args:
        detector: Any Detector implementing the IBVAP Detector protocol.
        frame: Full resolution input image (H, W, 3).
        frame_id: Current frame counter.
        slice_width: Tile width in pixels.
        slice_height: Tile height in pixels.
        overlap_ratio: Overlap percentage between tiles (0.1 to 0.3).
        nms_iou_threshold: IoU threshold for merging duplicates.

    Returns:
        List of Detection objects with global coordinates.
    """
    h, w = frame.shape[:2]
    # If frame is small, standard inference is sufficient
    if w <= slice_width and h <= slice_height:
        return detector.detect(frame, frame_id)

    tiles = slice_frame(frame, slice_width, slice_height, overlap_ratio)
    raw_detections: List[Detection] = []

    # 1. Detect on all tiles
    for tile, offset_x, offset_y in tiles:
        tile_dets = detector.detect(tile, frame_id)
        for det in tile_dets:
            bx1, by1, bx2, by2 = det.bbox
            global_box = (
                int(bx1 + offset_x),
                int(by1 + offset_y),
                int(bx2 + offset_x),
                int(by2 + offset_y),
            )
            raw_detections.append(
                Detection(
                    label=det.label,
                    confidence=det.confidence,
                    bbox=global_box,
                    class_id=det.class_id,
                    class_name=det.class_name,
                    frame_id=frame_id,
                    source=f"{det.source}_sahi",
                )
            )

    if not raw_detections:
        return []

    # 2. Global NMS across slices to eliminate duplicates on borders
    boxes = [[d.bbox[0], d.bbox[1], d.bbox[2] - d.bbox[0], d.bbox[3] - d.bbox[1]] for d in raw_detections]
    scores = [d.confidence for d in raw_detections]

    indices = cv2.dnn.NMSBoxes(
        boxes,
        scores,
        score_threshold=0.2,
        nms_threshold=nms_iou_threshold,
    )

    merged: List[Detection] = []
    if len(indices) > 0:
        indices = indices.flatten() if isinstance(indices, np.ndarray) else indices
        for idx in indices:
            merged.append(raw_detections[int(idx)])

    return merged
