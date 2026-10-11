"""Pixels -> quantities. Needs a scale (metres per pixel), which the baseline does not detect.

Scale is a user input on purpose: reading it from dimension text is a separate, error-prone
step, and a wrong scale silently multiplies every cost. The estimator should ask for it.
"""

from __future__ import annotations

import numpy as np
from skimage.morphology import skeletonize

from plan2cost.estimate import Quantity
from plan2cost.vision.rooms import Room, interior_area_px


def wall_length_px(walls: np.ndarray) -> float:
    """Centre-line length of the walls, in pixels (skeleton pixel count)."""
    return float(skeletonize(walls).sum())


def quantities_from_plan(
    walls: np.ndarray,
    rooms: list[Room],
    m_per_px: float,
    wall_height_m: float = 2.6,
    confidence: float = 1.0,
) -> list[Quantity]:
    """Floor area (m²), wall length (m) and wall surface (m², both faces) for pricing."""
    if m_per_px <= 0:
        raise ValueError("m_per_px must be positive")
    floor = interior_area_px(rooms) * m_per_px**2
    length = wall_length_px(walls) * m_per_px
    return [
        Quantity("floor_area", round(floor, 2), "m2", confidence),
        Quantity("wall_length", round(length, 2), "m", confidence),
        Quantity("wall_surface", round(length * wall_height_m * 2, 2), "m2", confidence),
    ]
