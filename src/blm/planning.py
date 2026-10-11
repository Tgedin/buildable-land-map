"""Municipal plan (PGOU) heights: what the plan allows, not just what the neighbours built.

Source for Valencia: "PGOU - Alineaciones", CC BY 4.0, ArcGIS REST layer on
geoportal.valencia.es. Each polygon has an `altura` text (e.g. "6", "B+5", "PROTEGIDO",
"0") and a `protec` code. See docs/decisions/0004-plan-heights.md.

ASSUMPTION (unverified against the plan's rules text): a numeric `altura` counts floors
above the ground floor, so allowed floors = altura + ground_floor_offset. Evidence: Catastro
floors are usually altura + 1 or + 2. The offset lives in config so it is easy to change.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from blm.config import AreaConfig, PlanningConfig

log = logging.getLogger(__name__)

PROTECTED_CODES = {"AMB", "PAR", "INT", "BRL"}
_PLAIN = re.compile(r"^\s*(?:<=\s*)?(\d+)\s*$")
_GROUND_PLUS = re.compile(r"^\s*B\s*\+\s*(\d+)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Altura:
    kind: str  # "floors" | "open" | "protected" | "unknown"
    floors: float  # NaN unless kind == "floors"


def parse_altura(altura: str | None, protec: str | None = None) -> Altura:
    """Classify one alignment polygon. Anything we cannot read is "unknown", never 0."""
    # pandas turns missing text into float NaN, so test the type, not truthiness.
    text = altura.strip().upper() if isinstance(altura, str) else ""
    code = protec.strip().upper() if isinstance(protec, str) else ""
    if text.startswith(("PROTEG", "PROTECC")) or code in PROTECTED_CODES:
        return Altura("protected", np.nan)
    if m := _PLAIN.match(text):
        n = int(m.group(1))
        # 0 means no building allowed (open space), different from "unknown".
        return Altura("open", np.nan) if n == 0 else Altura("floors", float(n))
    if m := _GROUND_PLUS.match(text):
        return Altura("floors", float(m.group(1)))
    return Altura("unknown", np.nan)


def classify_alignments(raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    parsed = [parse_altura(a, p) for a, p in zip(raw["altura"], raw["protec"], strict=True)]
    out = raw[["altura", "protec", "geometry"]].copy()
    out["kind"] = [a.kind for a in parsed]
    out["plan_floors"] = [a.floors for a in parsed]
    return out


def fetch_alignments(cfg: AreaConfig) -> gpd.GeoDataFrame:
    """Download the plan polygons intersecting cfg.bbox (paged ArcGIS REST query)."""
    url = cfg.planning.alignments_url
    if not url:
        raise ValueError("planning.alignments_url is not set in config/area.yaml")
    xmin, ymin, xmax, ymax = cfg.bbox
    params = {
        "where": "1=1",
        "geometry": f"{xmin},{ymin},{xmax},{ymax}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": cfg.epsg,
        "outSR": cfg.epsg,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "altura,protec",
        "f": "geojson",
    }
    frames, offset = [], 0
    while True:
        r = requests.get(
            f"{url}/query",
            params={**params, "resultOffset": offset},
            timeout=cfg.planning.timeout_s,
        )
        r.raise_for_status()
        body = r.json()
        page = gpd.GeoDataFrame.from_features(body["features"], crs=cfg.crs)
        if page.empty:
            break
        frames.append(page)
        offset += len(page)
        if not body.get("properties", {}).get("exceededTransferLimit"):
            break  # the server says there is no next page
    if not frames:
        return classify_alignments(
            gpd.GeoDataFrame(
                columns=["altura", "protec", "geometry"], geometry="geometry", crs=cfg.crs
            )
        )
    raw = pd.concat(frames, ignore_index=True)
    raw = gpd.GeoDataFrame(raw, geometry="geometry", crs=cfg.crs)
    log.info("Plan alignments: %d polygons", len(raw))
    return classify_alignments(raw)


def match_parcels(
    parcels: gpd.GeoDataFrame, alignments: gpd.GeoDataFrame, cfg: PlanningConfig
) -> gpd.GeoDataFrame:
    """Add plan_status, plan_floors, plan_allowed_floors and protected_share to each parcel.

    plan_status: "protected" | "open" | "floors" | "unknown". Protected wins over a height,
    because a protected building cannot be raised whatever its neighbours allow.
    """
    out = parcels.copy()
    area = out.set_index("refcat")["footprint_m2"]
    ov = gpd.overlay(
        out[["refcat", "geometry"]],
        alignments[["kind", "plan_floors", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    ov["ar"] = ov.geometry.area

    def share(kind: str) -> pd.Series:
        covered = ov[ov["kind"] == kind].groupby("refcat")["ar"].sum()
        return covered.reindex(area.index).fillna(0) / area

    protected, open_, floors = share("protected"), share("open"), share("floors")

    nums = ov[ov["kind"] == "floors"].sort_values("ar")
    dominant = nums.groupby("refcat")["plan_floors"].last().reindex(area.index)

    status = np.select(
        [
            protected >= cfg.protected_min_share,
            floors >= cfg.min_coverage,
            open_ >= cfg.protected_min_share,
        ],
        ["protected", "floors", "open"],
        default="unknown",
    )
    status = pd.Series(status, index=area.index)
    plan_floors = dominant.where(status == "floors")

    refcat = out["refcat"]
    out["plan_status"] = refcat.map(status)
    out["protected_share"] = refcat.map(protected).round(2)
    out["plan_floors"] = refcat.map(plan_floors)
    out["plan_allowed_floors"] = out["plan_floors"] + cfg.ground_floor_offset
    return out
