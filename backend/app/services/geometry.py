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


def ccw(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    """Returns True if points a, b, c are in counter-clockwise order."""
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(p1: tuple[float, float], p2: tuple[float, float],
                       p3: tuple[float, float], p4: tuple[float, float]) -> bool:
    """Check if line segment p1-p2 intersects segment p3-p4."""
    if (max(p1[0], p2[0]) < min(p3[0], p4[0]) or
        min(p1[0], p2[0]) > max(p3[0], p4[0]) or
        max(p1[1], p2[1]) < min(p3[1], p4[1]) or
        min(p1[1], p2[1]) > max(p3[1], p4[1])):
        return False

    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))


def point_side_of_line(point: tuple[float, float], line_a: tuple[float, float], line_b: tuple[float, float]) -> float:
    """Signed cross product indicating which side of directed line a->b the point lies on.
    > 0: left side (side A)
    < 0: right side (side B)
    """
    ax, ay = line_a
    bx, by = line_b
    px, py = point
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def check_line_crossing(
    p_prev: tuple[float, float],
    p_curr: tuple[float, float],
    line_a: tuple[float, float],
    line_b: tuple[float, float],
    direction_rule: str = "either"
) -> tuple[bool, str]:
    """Check if movement from p_prev to p_curr crosses line segment line_a->line_b.
    Returns (crossed: bool, direction: 'a_to_b' | 'b_to_a' | 'none')
    """
    if not segments_intersect(p_prev, p_curr, line_a, line_b):
        return False, "none"

    side_prev = point_side_of_line(p_prev, line_a, line_b)
    side_curr = point_side_of_line(p_curr, line_a, line_b)

    if side_prev > 0 and side_curr <= 0:
        dir_detected = "a_to_b"
    elif side_prev < 0 and side_curr >= 0:
        dir_detected = "b_to_a"
    else:
        dir_detected = "a_to_b" if side_prev >= 0 else "b_to_a"

    if direction_rule == "either":
        return True, dir_detected
    elif direction_rule == dir_detected:
        return True, dir_detected
    else:
        return False, dir_detected

