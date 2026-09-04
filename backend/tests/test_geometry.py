"""Tests for geometry service."""

import math
from backend.app.services.geometry import (
    point_in_polygon, polygon_centroid, polygon_area,
    point_distance, bbox_iou, bbox_center, direction_label,
)


def test_point_inside_simple_square():
    """Point should be inside a simple square polygon."""
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert point_in_polygon((50, 50), polygon) is True


def test_point_outside_simple_square():
    """Point should be outside the polygon."""
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert point_in_polygon((150, 50), polygon) is False


def test_point_on_boundary():
    """Point exactly on the boundary — implementation dependent."""
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
    # Edge points may or may not be detected; this tests consistency
    result = point_in_polygon((0, 50), polygon)
    assert isinstance(result, bool)


def test_polygon_centroid():
    """Centroid of a square should be at center."""
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
    cx, cy = polygon_centroid(polygon)
    assert abs(cx - 50) < 0.1
    assert abs(cy - 50) < 0.1


def test_polygon_area():
    """Area of a 100x100 square should be 10000."""
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
    area = polygon_area(polygon)
    assert abs(area - 10000) < 0.1


def test_point_distance():
    """Distance between (0,0) and (3,4) should be 5."""
    d = point_distance((0, 0), (3, 4))
    assert abs(d - 5.0) < 0.001


def test_bbox_iou_perfect_overlap():
    """Identical boxes should have IoU = 1."""
    box = (10, 10, 50, 50)
    iou = bbox_iou(box, box)
    assert abs(iou - 1.0) < 0.001


def test_bbox_iou_no_overlap():
    """Non-overlapping boxes should have IoU = 0."""
    box_a = (0, 0, 10, 10)
    box_b = (20, 20, 30, 30)
    iou = bbox_iou(box_a, box_b)
    assert abs(iou - 0.0) < 0.001


def test_bbox_center():
    """Center of (0,0,10,10) should be (5,5)."""
    assert bbox_center((0, 0, 10, 10)) == (5, 5)


def test_direction_label():
    """Direction vector to label mapping."""
    assert direction_label(10, 0) == "EAST"
    assert direction_label(-10, 0) == "WEST"
    assert direction_label(0, 10) == "SOUTH"
    assert direction_label(0, -10) == "NORTH"


def test_empty_polygon():
    """Empty polygon should not contain any point."""
    assert point_in_polygon((0, 0), []) is False
    assert point_in_polygon((0, 0), [[0, 0]]) is False
