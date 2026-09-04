#!/usr/bin/env python3
"""
IBVAP Map Tile Offline Pre-Caching Utility
==========================================
SIH PS-26187 | SSB, Ministry of Home Affairs

Pre-caches aerial satellite imagery or topographic map tiles into
frontend/public/tiles/{z}/{x}/{y}.png for 100% offline air-gapped field deployment.
"""

import argparse
import math
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Tile URL Templates
SOURCES = {
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "osm": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
}

# Border Outpost Coordinate Presets
PRESETS = {
    "bop-alpha": {
        "min_lat": 28.60,
        "max_lat": 28.63,
        "min_lon": 77.20,
        "max_lon": 77.23,
        "description": "Sector Alpha Outpost Range",
    },
    "indo-nepal-bop": {
        "min_lat": 27.42,
        "max_lat": 27.46,
        "min_lon": 83.20,
        "max_lon": 83.25,
        "description": "Indo-Nepal Strategic Border Outpost Range",
    },
}


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 decimal latitude and longitude to tile X and Y indices at zoom level."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def cache_tiles(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    min_zoom: int,
    max_zoom: int,
    output_dir: Path,
    source: str = "esri",
    dry_run: bool = False,
    delay: float = 0.05,
) -> int:
    """Download and cache tiles for specified geographic envelope."""
    url_template = SOURCES.get(source, SOURCES["esri"])
    headers = {"User-Agent": "IBVAP-Offline-Tile-Cacher/2.0 (SSB/MHA Border Security Platform)"}

    total_downloaded = 0
    total_skipped = 0
    tasks = []

    for z in range(min_zoom, max_zoom + 1):
        x_min, y_max = deg2num(min_lat, min_lon, z)
        x_max, y_min = deg2num(max_lat, max_lon, z)

        # Ensure correct ordering
        x_start, x_end = min(x_min, x_max), max(x_min, x_max)
        y_start, y_end = min(y_min, y_max), max(y_min, y_max)

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                tasks.append((z, x, y))

    print(f"\n=======================================================")
    print(f"IBVAP Offline Map Tile Pre-Caching")
    print(f"=======================================================")
    print(f"Source:     {source.upper()} ({url_template})")
    print(f"Target Dir: {output_dir}")
    print(f"Envelope:   LAT [{min_lat:.4f}, {max_lat:.4f}] | LON [{min_lon:.4f}, {max_lon:.4f}]")
    print(f"Zooms:      {min_zoom} -> {max_zoom}")
    print(f"Total Tiles: {len(tasks)}")
    print(f"Dry Run:    {dry_run}\n")

    if dry_run:
        print(f"[DRY RUN] Would fetch {len(tasks)} tiles.")
        return len(tasks)

    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, (z, x, y) in enumerate(tasks, start=1):
        tile_path = output_dir / str(z) / str(x) / f"{y}.png"
        if tile_path.exists() and tile_path.stat().st_size > 500:
            total_skipped += 1
            continue

        tile_path.parent.mkdir(parents=True, exist_ok=True)
        url = url_template.format(z=z, x=x, y=y)

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read()
                if len(content) > 200:
                    with open(tile_path, "wb") as f:
                        f.write(content)
                    total_downloaded += 1
                else:
                    print(f"⚠️  Small payload for tile {z}/{x}/{y}")
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            print(f"⚠️  Error fetching {url}: {e}")

        if idx % 10 == 0 or idx == len(tasks):
            print(f"\rProgress: {idx}/{len(tasks)} tiles evaluated (Downloaded: {total_downloaded}, Cached: {total_skipped})", end="")

    print(f"\n\n✅ Pre-caching complete. Downloaded: {total_downloaded}, Already Cached: {total_skipped}.")
    return total_downloaded


def main():
    parser = argparse.ArgumentParser(description="Cache satellite map tiles for offline air-gapped operations.")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Preset border bounding box")
    parser.add_argument("--min-lat", type=float, default=28.61, help="Minimum latitude")
    parser.add_argument("--max-lat", type=float, default=28.62, help="Maximum latitude")
    parser.add_argument("--min-lon", type=float, default=77.20, help="Minimum longitude")
    parser.add_argument("--max-lon", type=float, default=77.21, help="Maximum longitude")
    parser.add_argument("--min-zoom", type=int, default=12, help="Minimum zoom level (default 12)")
    parser.add_argument("--max-zoom", type=int, default=14, help="Maximum zoom level (default 14)")
    parser.add_argument("--source", choices=["esri", "osm"], default="esri", help="Tile provider source")
    parser.add_argument("--output-dir", type=str, default="frontend/public/tiles", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Print tile plan without network requests")
    parser.add_argument("--delay", type=float, default=0.02, help="Delay between requests in seconds")

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    out_path = project_root / args.output_dir

    if args.preset:
        p = PRESETS[args.preset]
        min_lat, max_lat = p["min_lat"], p["max_lat"]
        min_lon, max_lon = p["min_lon"], p["max_lon"]
        print(f"Using preset: {args.preset} — {p['description']}")
    else:
        min_lat, max_lat = args.min_lat, args.max_lat
        min_lon, max_lon = args.min_lon, args.max_lon

    cache_tiles(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        min_zoom=args.min_zoom,
        max_zoom=args.max_zoom,
        output_dir=out_path,
        source=args.source,
        dry_run=args.dry_run,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
