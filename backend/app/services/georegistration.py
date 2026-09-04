"""
WGS84 Camera-to-GPS Geo-Registration Engine
===========================================
Converts 2D CCTV / Thermal camera pixels into real-world WGS84 GPS coordinates
(Latitude, Longitude), Ground Distance (meters), and True Bearing (degrees).

Essential for military border surveillance:
When an intruder is detected in a camera frame, patrol Quick Reaction Teams (QRT)
must be dispatched to exact physical terrain coordinates, not pixel offsets.

Mathematical Model:
- Ground-plane planar ray-casting from camera optical center
- Vertical FOV derived from horizontal FOV and aspect ratio
- Depression angle = Camera Tilt + Pixel Vertical Angle
- Ground Distance d = Camera_Height / tan(Depression_Angle)
- Forward Geodetic Projection on WGS84 Reference Ellipsoid
"""

from __future__ import annotations
import math
from typing import Dict, Any, Tuple


# WGS84 Equatorial Radius in meters
WGS84_A = 6378137.0


def project_pixel_to_gps(
    pixel_x: float,
    pixel_y: float,
    camera_lat: float,
    camera_lon: float,
    camera_height_m: float = 12.0,
    tilt_deg: float = 15.0,
    heading_deg: float = 0.0,
    hfov_deg: float = 65.0,
    frame_width: int = 1280,
    frame_height: int = 720,
) -> Dict[str, Any]:
    """Project a 2D bounding box foot/center pixel to real-world WGS84 GPS coordinates.

    Args:
        pixel_x: X coordinate in image [0, frame_width]
        pixel_y: Y coordinate in image [0, frame_height] (bottom center of bbox is best for ground foot)
        camera_lat: Camera mounting latitude in degrees (WGS84)
        camera_lon: Camera mounting longitude in degrees (WGS84)
        camera_height_m: Camera height above ground in meters (e.g. watchtower height)
        tilt_deg: Camera downward tilt angle from horizon in degrees (positive downwards)
        heading_deg: Camera optical axis true bearing in degrees [0, 360] (0 = North, 90 = East)
        hfov_deg: Horizontal Field of View of camera lens in degrees
        frame_width: Image resolution width
        frame_height: Image resolution height

    Returns:
        Dictionary with target GPS coordinates, distance, bearing, and formatting.
    """
    # 1. Image normalized coordinates [-0.5, 0.5] from optical center
    nx = (pixel_x - (frame_width / 2.0)) / frame_width
    ny = (pixel_y - (frame_height / 2.0)) / frame_height

    # 2. Field of view calculations
    hfov_rad = math.radians(hfov_deg)
    aspect_ratio = frame_height / frame_width
    # Vertical FOV derived from pinhole camera model
    vfov_rad = 2.0 * math.atan(math.tan(hfov_rad / 2.0) * aspect_ratio)

    # 3. Ray angles relative to optical axis
    alpha_x = nx * hfov_rad  # Azimuth offset (radians)
    alpha_y = ny * vfov_rad  # Elevation offset downward (radians)

    # 4. Total depression angle from horizon (tilt + pixel angle)
    tilt_rad = math.radians(tilt_deg)
    depression_angle = tilt_rad + alpha_y

    # Clamp depression angle to prevent horizon infinity division
    min_depression = math.radians(1.5)  # 1.5 degrees minimum downward angle
    if depression_angle < min_depression:
        depression_angle = min_depression

    # 5. Ground distance calculation (h / tan(theta))
    ground_distance = camera_height_m / math.tan(depression_angle)
    # Clamp distance to realistic border camera optical range (max 3500 meters)
    ground_distance = min(ground_distance, 3500.0)

    # 6. Target True Azimuth / Bearing from North
    ray_azimuth_deg = math.degrees(alpha_x)
    target_bearing = (heading_deg + ray_azimuth_deg) % 360.0

    # 7. Forward Geodetic Projection (Great Circle / Haversine Forward)
    # Earth radius approximation at current latitude
    lat_rad = math.radians(camera_lat)
    lon_rad = math.radians(camera_lon)
    bearing_rad = math.radians(target_bearing)

    angular_distance = ground_distance / WGS84_A

    target_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance)
        + math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    target_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(target_lat_rad),
    )

    target_lat = math.degrees(target_lat_rad)
    target_lon = math.degrees(target_lon_rad)

    # Human-readable military coordinates string
    ns = "N" if target_lat >= 0 else "S"
    ew = "E" if target_lon >= 0 else "W"
    coord_str = f"{abs(target_lat):.5f}° {ns}, {abs(target_lon):.5f}° {ew}"

    return {
        "target_latitude": round(target_lat, 6),
        "target_longitude": round(target_lon, 6),
        "ground_distance_m": round(ground_distance, 1),
        "bearing_deg": round(target_bearing, 1),
        "camera_height_m": round(camera_height_m, 1),
        "coordinate_string": coord_str,
    }
