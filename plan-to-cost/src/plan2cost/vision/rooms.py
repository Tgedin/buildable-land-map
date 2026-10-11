"""Find enclosed rooms as the free space the walls fence in.

Free space touching the image border is the outside, not a room. Door openings are not
closed, so two rooms joined by a doorway come out as one region: use total interior area
(`interior_area_px`), which does not care, rather than the room count, for quantities.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class Room:
    area_px: int
    centroid: tuple[float, float]  # (x, y) in pixels


def find_rooms(walls: np.ndarray, min_area_frac: float = 0.002) -> list[Room]:
    free = (~walls).astype(np.uint8)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(free, connectivity=4)
    h, w = walls.shape
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    min_area = walls.size * min_area_frac
    rooms = []
    for label in range(1, n):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if label in border or area < min_area:
            continue
        rooms.append(Room(area, (float(centroids[label][0]), float(centroids[label][1]))))
    return rooms


def interior_area_px(rooms: list[Room]) -> int:
    return sum(r.area_px for r in rooms)
