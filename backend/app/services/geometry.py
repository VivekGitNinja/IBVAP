"""
Geometry service — point-in-polygon, polygon area, centroid,
distance calculations, and zone membership.
"""

from __future__ import annotations
import math


def point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    """Ray-casting algorithm for point-in-polygon test."""
    x, y = point
    if len(polygon) < 3:
        return False
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def polygon_centroid(polygon: list[list[float]]) -> tuple[float, float]:
    """Compute centroid of a polygon."""
    if not polygon:
        return (0.0, 0.0)
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    return (cx, cy)


def polygon_area(polygon: list[list[float]]) -> float:
    """Compute area of a polygon using the shoelace formula."""
    if len(polygon) < 3:
        return 0.0
    area = 0.0
    n = len(polygon)
    for i in range(n):
        j = (i + 1) % n
        area += polygon[i][0] * polygon[j][1]
        area -= polygon[j][0] * polygon[i][1]
    return abs(area) / 2.0


def point_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


def bbox_iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    """Compute IoU (Intersection over Union) between two bounding boxes."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(1, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(1, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
    union = area_a + area_b - inter

    return inter / max(union, 1)


def bbox_center(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    """Center point of a bounding box."""
    return ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)


def direction_label(dx: float, dy: float) -> str:
    """Map direction vector to cardinal label."""
    if abs(dx) < abs(dy):
        return "SOUTH" if dy > 0 else "NORTH"
    return "EAST" if dx > 0 else "WEST"
