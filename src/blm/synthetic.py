"""Synthetic neighbourhood + point cloud with known ground truth.

Used by tests and by `blm sample` so the web map works before any real data
is downloaded. Everything produced here is flagged `synthetic: true`.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import laspy
import numpy as np
import shapely
from shapely.geometry import box

from blm.lidar import PointCloud

FLOOR_H = 3.0


def make_parts(
    origin: tuple[float, float] = (440300.0, 4473500.0),
    blocks: tuple[int, int] = (4, 3),
    parcels_per_side: int = 5,
    crs: str = "EPSG:25830",
    seed: int = 7,
) -> gpd.GeoDataFrame:
    """Blocks of 5 parcels per side separated by 12 m streets. Most parcels have
    5–7 floors; ~15% are deliberately low (1–2 floors) to create gaps."""
    rng = np.random.default_rng(seed)
    parcel_w, depth, street = 14.0, 16.0, 12.0
    block_w = parcels_per_side * parcel_w
    block_h = 2 * depth
    records, n = [], 0
    for bx in range(blocks[0]):
        for by in range(blocks[1]):
            x0 = origin[0] + bx * (block_w + street)
            y0 = origin[1] + by * (block_h + street)
            for row in range(2):
                for i in range(parcels_per_side):
                    n += 1
                    floors = (
                        int(rng.choice([1, 2])) if rng.random() < 0.15 else int(rng.integers(5, 8))
                    )
                    geom = box(
                        x0 + i * parcel_w + 0.2,
                        y0 + row * depth + 0.2,
                        x0 + (i + 1) * parcel_w - 0.2,
                        y0 + (row + 1) * depth - 0.2,
                    )
                    refcat = f"{n:07d}SYN{bx}{by}{row}{i}A"[:14]
                    records.append(
                        {
                            "part_id": f"{refcat}_part1",
                            "refcat": refcat,
                            "floors_above": floors,
                            "floors_below": 0,
                            "geometry": geom,
                        }
                    )
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=crs)
    gdf["footprint_m2"] = gdf.geometry.area.round(1)
    return gdf


def make_point_cloud(parts: gpd.GeoDataFrame, density: float = 2.0, seed: int = 7) -> PointCloud:
    """Ground (class 2) everywhere off-building on a gentle slope; roofs (class 6)
    at ground + floors × 3 m + 0.5 m parapet, with 0.15 m noise."""
    rng = np.random.default_rng(seed)
    xmin, ymin, xmax, ymax = parts.total_bounds
    xmin, ymin, xmax, ymax = xmin - 15, ymin - 15, xmax + 15, ymax + 15
    n = int((xmax - xmin) * (ymax - ymin) * density)
    x = rng.uniform(xmin, xmax, n)
    y = rng.uniform(ymin, ymax, n)
    ground_z = 650.0 + 0.01 * (x - xmin) + 0.005 * (y - ymin)
    z = ground_z.copy()
    cls = np.full(n, 2, dtype=np.uint8)

    for geom, floors in zip(parts.geometry, parts["floors_above"], strict=True):
        inside = shapely.contains_xy(geom, x, y)
        z[inside] = ground_z[inside] + floors * FLOOR_H + 0.5
        cls[inside] = 6
    z += rng.normal(0, 0.15, n)
    return PointCloud(x, y, z, cls)


def write_laz(pc: PointCloud, path: Path) -> None:
    header = laspy.LasHeader(point_format=1, version="1.2")
    header.offsets = [float(pc.x.min()), float(pc.y.min()), float(pc.z.min())]
    header.scales = [0.01, 0.01, 0.01]
    las = laspy.LasData(header)
    las.x, las.y, las.z = pc.x, pc.y, pc.z
    las.classification = pc.cls
    las.write(path)
