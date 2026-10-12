"""Download and parse Catastro INSPIRE buildings (BU) via WFS.

Service: https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx
Limits (official docs): 4 km² bbox and 5,000 features per request.

We fetch BU.BUILDINGPART because it carries `numberOfFloorsAboveGround`;
BU.BUILDING does not. A parcel (refcat, 14 chars) has one or more parts.
BU.BUILDING is fetched too, only for `currentUse` (residential, industrial, public services…).
"""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import MultiPolygon, Polygon

from blm.config import AreaConfig

log = logging.getLogger(__name__)

WFS_URL = "https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx"
TYPENAME = "BU.BUILDINGPART"
BUILDING_TYPENAME = "BU.BUILDING"

BBox = tuple[float, float, float, float]


# ---------------------------------------------------------------- tiling


def tile_bbox(bbox: BBox, tile_size: float) -> list[BBox]:
    """Split a bbox into a grid of tiles no larger than tile_size × tile_size."""
    xmin, ymin, xmax, ymax = bbox
    tiles: list[BBox] = []
    y = ymin
    while y < ymax:
        x = xmin
        y2 = min(y + tile_size, ymax)
        while x < xmax:
            x2 = min(x + tile_size, xmax)
            tiles.append((x, y, x2, y2))
            x = x2
        y = y2
    return tiles


def split_in_four(b: BBox) -> list[BBox]:
    xmin, ymin, xmax, ymax = b
    xm, ym = (xmin + xmax) / 2, (ymin + ymax) / 2
    return [(xmin, ymin, xm, ym), (xm, ymin, xmax, ym), (xmin, ym, xm, ymax), (xm, ym, xmax, ymax)]


# ---------------------------------------------------------------- parsing


def _local(tag: str) -> str:
    """'{namespace}name' -> 'name'. Parsing is namespace-agnostic on purpose:
    INSPIRE schema versions change prefixes, local names stay stable."""
    return tag.rsplit("}", 1)[-1]


def _find(el: ET.Element, name: str) -> ET.Element | None:
    for child in el.iter():
        if _local(child.tag) == name:
            return child
    return None


def _ring(pos_list: str) -> list[tuple[float, float]]:
    vals = [float(v) for v in pos_list.split()]
    return list(zip(vals[0::2], vals[1::2], strict=True))


def _geometry(part: ET.Element) -> Polygon | MultiPolygon | None:
    polygons: list[Polygon] = []
    for patch in part.iter():
        if _local(patch.tag) not in {"PolygonPatch", "Polygon"}:
            continue
        exterior, holes = None, []
        for child in patch:
            pos = _find(child, "posList")
            if pos is None or not pos.text:
                continue
            if _local(child.tag) == "exterior":
                exterior = _ring(pos.text)
            elif _local(child.tag) == "interior":
                holes.append(_ring(pos.text))
        if exterior:
            polygons.append(Polygon(exterior, holes))
    if not polygons:
        return None
    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)


def _int_or_none(el: ET.Element | None) -> int | None:
    if el is None or el.text is None or not el.text.strip():
        return None
    try:
        return int(float(el.text))
    except ValueError:
        return None


class WfsError(RuntimeError):
    pass


@dataclass
class ParsedParts:
    records: list[dict]
    n_features: int


def _exception_text(root: ET.Element) -> str:
    return " ".join(t.strip() for t in root.itertext() if t.strip())


def _is_empty_answer(root: ET.Element) -> bool:
    """A tile with no buildings (sea, fields) is answered with an *exception*, not an empty list.

    "No records founded for BBOX and SRS provided" is a complete, valid answer: nothing there.
    """
    return _local(root.tag) == "ExceptionReport" and "No records" in _exception_text(root)


def _raise_if_exception(root: ET.Element) -> None:
    if _local(root.tag) == "ExceptionReport":
        raise WfsError(f"WFS exception: {_exception_text(root)}")


def parse_building_parts(xml_bytes: bytes) -> ParsedParts:
    """Parse a WFS GetFeature response into records with geometry + floors."""
    root = ET.fromstring(xml_bytes)
    if _is_empty_answer(root):
        return ParsedParts(records=[], n_features=0)
    _raise_if_exception(root)

    records: list[dict] = []
    for el in root.iter():
        if _local(el.tag) != "BuildingPart":
            continue
        local_id_el = _find(el, "localId")
        local_id = (
            local_id_el.text.strip() if local_id_el is not None and local_id_el.text else None
        )
        geom = _geometry(el)
        if not local_id or geom is None:
            continue
        records.append(
            {
                "part_id": local_id,
                "refcat": local_id.split("_")[0][:14],
                "floors_above": _int_or_none(_find(el, "numberOfFloorsAboveGround")),
                "floors_below": _int_or_none(_find(el, "numberOfFloorsBelowGround")),
                "geometry": geom,
            }
        )
    return ParsedParts(records=records, n_features=len(records))


def parse_building_uses(xml_bytes: bytes) -> ParsedParts:
    """Parse a BU.BUILDING response into {refcat, current_use} records (no geometry)."""
    root = ET.fromstring(xml_bytes)
    if _is_empty_answer(root):
        return ParsedParts(records=[], n_features=0)
    _raise_if_exception(root)

    records: list[dict] = []
    for el in root.iter():
        if _local(el.tag) != "Building":
            continue
        local_id_el = _find(el, "localId")
        use_el = _find(el, "currentUse")
        if local_id_el is None or not local_id_el.text:
            continue
        use = use_el.text.strip() if use_el is not None and use_el.text else ""
        # Missing use stays None: "unknown" is not the same fact as "residential".
        records.append({"refcat": local_id_el.text.strip()[:14], "current_use": use or None})
    return ParsedParts(records=records, n_features=len(records))


# ---------------------------------------------------------------- fetching


def _cache_path(cfg: AreaConfig, typename: str, b: BBox) -> Path:
    key = "_".join(f"{v:.0f}" for v in b)
    return cfg.raw_dir / "catastro" / cfg.name / f"{typename}_{key}.xml"


def _get(session: requests.Session, b: BBox, cfg: AreaConfig, typename: str = TYPENAME) -> bytes:
    """One WFS response, from the on-disk cache when we already have it.

    Every tile is saved under data/raw so an interrupted city-scale fetch resumes where it
    stopped instead of starting again. Only complete responses are cached (written to a
    `.part` file first), and errors are never cached.
    """
    cache = _cache_path(cfg, typename, b)
    if cache.exists() and cache.stat().st_size > 0:
        return cache.read_bytes()
    params = {
        "service": "wfs",
        "version": "2.0.0",
        "request": "getfeature",
        "typenames": typename,
        "bbox": ",".join(f"{v:.2f}" for v in b),
        "srsname": f"EPSG::{cfg.epsg}",
    }
    for attempt in range(3):
        try:
            r = session.get(WFS_URL, params=params, timeout=cfg.catastro.timeout_s)
            r.raise_for_status()
            if b"ExceptionReport" not in r.content[:2000] or b"No records" in r.content[:2000]:
                cache.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.rename(cache)
            if cfg.catastro.request_delay_s:
                time.sleep(cfg.catastro.request_delay_s)
            return r.content
        except requests.RequestException as exc:
            wait = 2**attempt
            log.warning("WFS request failed (%s), retry in %ss", exc, wait)
            time.sleep(wait)
    raise WfsError(f"WFS request failed 3 times for bbox {b}")


def _fetch_tile(
    session: requests.Session,
    b: BBox,
    cfg: AreaConfig,
    typename: str = TYPENAME,
    parse=parse_building_parts,
    depth: int = 0,
) -> Iterator[dict]:
    parsed = parse(_get(session, b, cfg, typename))
    if parsed.n_features >= cfg.catastro.max_features_per_request and depth < 4:
        log.info("Tile %s hit the feature cap, splitting", b)
        for sub in split_in_four(b):
            yield from _fetch_tile(session, sub, cfg, typename, parse, depth + 1)
        return
    yield from parsed.records


def _tiles_in_parallel(cfg: AreaConfig, typename: str, parse) -> Iterator[list[dict]]:
    """The records of each tile, in tile order, fetched by `cfg.catastro.workers` threads.

    Each tile gets its own session (a Session is not guaranteed thread-safe). Results come back in
    order, so the output does not depend on how many workers ran.
    """
    tiles = tile_bbox(cfg.bbox, cfg.catastro.tile_size_m)
    log.info("%s: %d tile(s), %d worker(s)", typename, len(tiles), cfg.catastro.workers)

    def one(t: BBox) -> list[dict]:
        with requests.Session() as session:
            return list(_fetch_tile(session, t, cfg, typename, parse))

    with ThreadPoolExecutor(max_workers=max(1, cfg.catastro.workers)) as pool:
        for i, recs in enumerate(pool.map(one, tiles), 1):
            if i % 25 == 0 or i == len(tiles):
                log.info("  %s tile %d/%d done", typename, i, len(tiles))
            yield recs


def fetch_building_uses(cfg: AreaConfig) -> dict[str, str | None]:
    """Fetch BU.BUILDING in cfg.bbox and return {refcat: current_use}."""
    uses: dict[str, str | None] = {}
    for recs in _tiles_in_parallel(cfg, BUILDING_TYPENAME, parse_building_uses):
        for rec in recs:
            uses[rec["refcat"]] = rec["current_use"]
    log.info("Fetched current use for %d buildings", len(uses))
    return uses


def fetch_building_parts(cfg: AreaConfig) -> gpd.GeoDataFrame:
    """Fetch all building parts in cfg.bbox, deduplicated by part_id."""
    records: dict[str, dict] = {}
    for recs in _tiles_in_parallel(cfg, TYPENAME, parse_building_parts):
        for rec in recs:
            records[rec["part_id"]] = rec  # parts crossing tile edges appear twice
    log.info("Fetched %d building parts", len(records))
    return to_geodataframe(list(records.values()), cfg.crs)


def to_geodataframe(records: list[dict], crs: str) -> gpd.GeoDataFrame:
    cols = ["part_id", "refcat", "floors_above", "floors_below", "geometry"]
    gdf = gpd.GeoDataFrame(records or None, columns=cols, geometry="geometry", crs=crs)
    gdf["footprint_m2"] = gdf.geometry.area.round(1)
    return gdf


def load_from_files(paths: list[Path], crs: str) -> gpd.GeoDataFrame:
    """Offline path: parse WFS responses saved by hand (e.g. from a browser)."""
    records: dict[str, dict] = {}
    for p in paths:
        for rec in parse_building_parts(p.read_bytes()).records:
            records[rec["part_id"]] = rec
    return to_geodataframe(list(records.values()), crs)
