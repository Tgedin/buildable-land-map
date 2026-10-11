"""Download the LiDAR .laz sheets that cover the area, from a published sheet index.

Valencia: the ICV publishes a WFS index (one polygon per 2x2 km sheet, with `nom_laz` and
`link_laz`). Reading it lets CI and a fresh clone get exactly the sheets they need, with no
login. CNIG's own download centre blocks scripted access, so it cannot be used for this.
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import box

from blm.config import AreaConfig

log = logging.getLogger(__name__)


def fetch_index(url: str, crs: str, timeout: int) -> gpd.GeoDataFrame:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "buildable-land-map"})
    r.raise_for_status()
    return gpd.GeoDataFrame.from_features(r.json()["features"], crs=crs)


def sheets_for_bbox(
    index: gpd.GeoDataFrame, bbox: tuple[float, float, float, float]
) -> list[tuple[str, str]]:
    """(file name, url) of every sheet whose polygon touches the bbox."""
    hit = index[index.intersects(box(*bbox))]
    return sorted(zip(hit["nom_laz"], hit["link_laz"], strict=True))


def download_sheets(cfg: AreaConfig, dest: Path) -> list[Path]:
    """Fetch the sheets covering cfg.bbox into dest. Files already there are kept."""
    url = cfg.lidar.sheet_index_url
    if not url:
        raise ValueError("lidar.sheet_index_url is not set in config/area.yaml")
    sheets = sheets_for_bbox(fetch_index(url, cfg.crs, cfg.lidar.download_timeout_s), cfg.bbox)
    if not sheets:
        raise ValueError("No LiDAR sheet in the index covers the bbox")
    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, link in sheets:
        path = dest / name
        paths.append(path)
        if path.exists() and path.stat().st_size > 0:
            log.info("LiDAR sheet already present: %s", name)
            continue
        log.info("Downloading LiDAR sheet %s", name)
        tmp = path.with_suffix(".part")  # a half-downloaded file must never look complete
        with requests.get(link, stream=True, timeout=cfg.lidar.download_timeout_s) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        tmp.rename(path)
    return paths
