"""Municipal plan (PGOU) heights: what the plan allows, not just what the neighbours built.

Source for Valencia: "PGOU - Alineaciones", CC BY 4.0, ArcGIS REST layer on
geoportal.valencia.es. Each polygon has an `altura` text (e.g. "6", "B+5", "PROTEGIDO",
"0") and a `protec` code. See docs/decisions/0004-plan-heights.md.

The plan's floor count INCLUDES the ground floor (Normas Urbanísticas art. 5.33: "número de
plantas por encima de la cota de referencia o de la rasante, incluida la planta baja"; art.
6.19.1 uses "el señalado en los planos menos uno" for floors above it), so allowed floors =
altura + 0. The remaining assumption is that the layer's `altura` is the Plano C number. The
offset stays in config so a reader can see the earlier +1 reading (ADR 0004).
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


def _fetch_layer(url: str, fields: str, cfg: AreaConfig) -> gpd.GeoDataFrame:
    """Page through an ArcGIS REST layer for the polygons intersecting cfg.bbox."""
    xmin, ymin, xmax, ymax = cfg.bbox
    params = {
        "where": "1=1",
        "geometry": f"{xmin},{ymin},{xmax},{ymax}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": cfg.epsg,
        "outSR": cfg.epsg,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": fields,
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
        cols = [*fields.split(","), "geometry"]
        return gpd.GeoDataFrame(columns=cols, geometry="geometry", crs=cfg.crs)
    raw = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(raw, geometry="geometry", crs=cfg.crs)


def fetch_alignments(cfg: AreaConfig) -> gpd.GeoDataFrame:
    """Download the plan polygons intersecting cfg.bbox (paged ArcGIS REST query)."""
    url = cfg.planning.alignments_url
    if not url:
        raise ValueError("planning.alignments_url is not set in config/area.yaml")
    raw = _fetch_layer(url, "altura,protec", cfg)
    log.info("Plan alignments: %d polygons", len(raw))
    return classify_alignments(raw)


def fetch_zoning(cfg: AreaConfig) -> gpd.GeoDataFrame:
    """Download the plan's zone polygons (`califi`: ENS, RV, ...) intersecting cfg.bbox."""
    url = cfg.planning.zoning_url
    if not url:
        raise ValueError("planning.zoning_url is not set in config/area.yaml")
    raw = _fetch_layer(url, "califi", cfg)
    out = raw[["califi", "geometry"]].copy()
    out["califi"] = out["califi"].astype("string").str.strip().replace("", pd.NA)
    log.info("Plan zoning: %d polygons", len(out))
    return out


def match_zone(
    parcels: gpd.GeoDataFrame, zoning: gpd.GeoDataFrame, min_share: float = 0.5
) -> gpd.GeoDataFrame:
    """Add `zone`: the zone code covering most of the parcel, or None if no code covers half.

    Never guessed: a parcel split between zones, or outside every polygon, has no zone.
    """
    out = parcels.copy()
    area = out.set_index("refcat")["footprint_m2"]
    ov = gpd.overlay(
        out[["refcat", "geometry"]],
        zoning.dropna(subset=["califi"])[["califi", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    ov["ar"] = ov.geometry.area
    by_zone = ov.groupby(["refcat", "califi"])["ar"].sum().reset_index()
    best = by_zone.sort_values("ar").groupby("refcat").last()
    share = best["ar"] / area.reindex(best.index)
    zone = best["califi"].where(share >= min_share)
    mapped = out["refcat"].map(zone)
    out["zone"] = mapped.astype(object).where(mapped.notna(), None)
    return out


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
