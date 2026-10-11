"""Find walls in a plan image: dark, thick strokes.

Thin dark things (dimension lines, text, furniture outlines, door arcs) are removed by a
morphological opening whose size scales with the image, so it works across resolutions.
Walls drawn as hatching or in colour are NOT handled by this baseline.
"""

from __future__ import annotations

import cv2
import numpy as np


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:  # drop alpha, treating transparent as white
        alpha = image[:, :, 3:4] / 255.0
        image = (image[:, :, :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def wall_mask(
    gray: np.ndarray,
    open_frac: float = 0.006,
    min_blob_frac: float = 0.0005,
    close_frac: float = 0.0,
) -> np.ndarray:
    """Boolean mask, True where a wall is.

    open_frac: opening kernel as a fraction of the shorter image side (strokes thinner than
        this are not walls).
    min_blob_frac: drop connected blobs smaller than this fraction of the image area.
    close_frac: before filtering, merge strokes closer than this fraction of the shorter
        side. Scanned plans often draw a wall as two thin parallel lines or as hatching, which
        only counts as a wall once the lines are merged. 0 turns it off.
    """
    _, dark = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if close_frac > 0:
        kc = max(3, int(round(min(gray.shape) * close_frac)))
        dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((kc, kc), np.uint8))
    k = max(3, int(round(min(gray.shape) * open_frac)))
    opened = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    min_area = gray.size * min_blob_frac
    keep = np.zeros(n, dtype=bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area  # label 0 is the background
    return keep[labels]
