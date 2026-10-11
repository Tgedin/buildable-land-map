"""Measure real building heights from PNOA LiDAR point clouds.

height = median(z of building-class points inside the footprint)
       - median(z of ground-class points in a ring around the footprint)

Medians, not max/min: robust to chimneys, antennas, trees and classification noise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import laspy
import numpy as np
import shapely

from blm.config import LidarConfig

log = logging.getLogger(__name__)


@dataclass
class PointCloud:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    cls: np.ndarray

    def __len__(self) -> int:
        return len(self.x)

    def subset(self, mask: np.ndarray) -> PointCloud:
        return PointCloud(self.x[mask], self.y[mask], self.z[mask], self.cls[mask])


def read_laz(
    paths: list[Path], bbox: tuple[float, float, float, float], keep: set[int]
) -> PointCloud:
    """Read LAS/LAZ tiles, keeping only points of the given classes inside bbox."""
    xs, ys, zs, cs = [], [], [], []
    xmin, ymin, xmax, ymax = bbox
    for p in paths:
        las = laspy.read(p)
        x, y, z = np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)
        c = np.asarray(las.classification)
        m = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax) & np.isin(c, list(keep))
        xs.append(x[m])
        ys.append(y[m])
        zs.append(z[m])
        cs.append(c[m])
        log.info("  %s: kept %d / %d points", p.name, int(m.sum()), len(x))
    if not xs:
        empty = np.empty(0)
        return PointCloud(empty, empty, empty, empty.astype(np.uint8))
    return PointCloud(
        np.concatenate(xs), np.concatenate(ys), np.concatenate(zs), np.concatenate(cs)
    )


class GridIndex:
    """Bucket points into square cells so each footprint only scans nearby points.
    Turns O(points × buildings) into roughly O(points + buildings)."""

    def __init__(self, pc: PointCloud, cell: float = 25.0):
        self.pc, self.cell = pc, cell
        self.x0, self.y0 = (pc.x.min(), pc.y.min()) if len(pc) else (0.0, 0.0)
        ix = ((pc.x - self.x0) // cell).astype(np.int64)
        iy = ((pc.y - self.y0) // cell).astype(np.int64)
        self.ny = int(iy.max()) + 1 if len(pc) else 1
        keys = ix * self.ny + iy
        self.order = np.argsort(keys, kind="stable")
        self.sorted_keys = keys[self.order]

    def query(self, bounds: tuple[float, float, float, float]) -> np.ndarray:
        """Indices of points in cells overlapping bounds (superset; filter after)."""
        if not len(self.pc):
            return np.empty(0, dtype=np.int64)
        bx0, by0, bx1, by1 = bounds
        ix0, ix1 = int((bx0 - self.x0) // self.cell), int((bx1 - self.x0) // self.cell)
        iy0, iy1 = int((by0 - self.y0) // self.cell), int((by1 - self.y0) // self.cell)
        iy0, iy1 = max(iy0, 0), min(iy1, self.ny - 1)
        out = []
        for ix in range(max(ix0, 0), ix1 + 1):
            lo = np.searchsorted(self.sorted_keys, ix * self.ny + iy0, side="left")
            hi = np.searchsorted(self.sorted_keys, ix * self.ny + iy1, side="right")
            out.append(self.order[lo:hi])
        return np.concatenate(out) if out else np.empty(0, dtype=np.int64)


def building_heights(parts: gpd.GeoDataFrame, pc: PointCloud, cfg: LidarConfig) -> gpd.GeoDataFrame:
    """Add lidar_height_m, lidar_roof_pts, lidar_ground_pts, lidar_confidence columns."""
    index = GridIndex(pc)
    heights, n_roof, n_ground, conf = [], [], [], []

    for geom in parts.geometry:
        roof_zone = geom.buffer(-cfg.inner_buffer_m)
        if roof_zone.is_empty:
            roof_zone = geom
        ring = geom.buffer(cfg.ground_ring_m).difference(geom)

        idx = index.query(ring.bounds)  # ring bounds cover the footprint too
        x, y, z, c = pc.x[idx], pc.y[idx], pc.z[idx], pc.cls[idx]

        roof_m = (c == cfg.building_class) & shapely.contains_xy(roof_zone, x, y)
        ground_m = (c == cfg.ground_class) & shapely.contains_xy(ring, x, y)
        nr, ng = int(roof_m.sum()), int(ground_m.sum())

        if nr and ng:
            h = float(np.median(z[roof_m]) - np.median(z[ground_m]))
            heights.append(round(max(h, 0.0), 2))
        else:
            heights.append(np.nan)
        n_roof.append(nr)
        n_ground.append(ng)
        conf.append("high" if nr >= cfg.min_roof_points and ng >= 5 else "low")

    out = parts.copy()
    out["lidar_height_m"] = heights
    out["lidar_roof_pts"] = n_roof
    out["lidar_ground_pts"] = n_ground
    out["lidar_confidence"] = conf
    return out
