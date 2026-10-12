"""Write the static files the web map reads: parcels.geojson + summary.json."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import numpy as np

WEB_COLUMNS = [
    "refcat",
    "floors",
    "dominant_floors",
    "gap_floors",
    "gap_m2",
    "existing_m2",
    "footprint_m2",
    "current_use",
    "plan_status",
    "plan_floors",
    "plan_allowed_floors",
    "plan_gap_floors",
    "plan_gap_m2",
    "gap_class",
    "protected_share",
    "lidar_height_m",
    "lidar_confidence",
]


def export_web(
    parcels: gpd.GeoDataFrame,
    summary: dict,
    out_dir: Path,
    label: str,
    precision: int = 6,
    synthetic: bool = False,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = [c for c in WEB_COLUMNS if c in parcels.columns]
    web = parcels[cols + ["geometry"]].to_crs(4326)
    web["geometry"] = web.geometry.set_precision(10 ** (-precision))
    web = web.replace({np.nan: None})

    geojson_path = out_dir / "parcels.geojson"
    geojson_path.write_text(web.to_json(drop_id=True), encoding="utf-8")

    summary_out = {
        **summary,
        "label": label,
        "synthetic": synthetic,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "bounds_wgs84": [round(v, precision) for v in web.total_bounds.tolist()],
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_out, indent=2), encoding="utf-8")
    return geojson_path, summary_path


def export_candidates(
    parcels: gpd.GeoDataFrame,
    refcats: set[str],
    summary: dict,
    out_dir: Path,
    label: str,
    precision: int = 6,
) -> tuple[Path, Path]:
    """Export only the parcels in `refcats` (those the screening found something on).

    A whole city has too many parcels for a static web page (ADR 0006); the map only needs the
    ones with a result. The summary still describes every parcel.
    """
    chosen = parcels[parcels["refcat"].isin(refcats)]
    return export_web(chosen, summary, out_dir, label, precision)


def export_parts(
    parts: gpd.GeoDataFrame,
    out_dir: Path,
    refcats: set[str] | None = None,
    precision: int = 6,
) -> Path:
    """Write parts.geojson: each building part with its own floors, for the 3D layer.

    A parcel's outline extruded at its tallest height draws a small tower on a big plot as a
    giant slab. Parts keep their own heights, and `main` marks the parts at the parcel's tallest
    height: those are where an addition would go, so the candidate view colours only those.
    `refcats` limits the export (a city only needs the parcels with a result).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    p = parts[["refcat", "floors_above", "geometry"]].copy()
    if refcats is not None:
        p = p[p["refcat"].isin(refcats)]
    tallest = p.groupby("refcat")["floors_above"].transform("max")
    p["main"] = (p["floors_above"] == tallest) & p["floors_above"].notna()
    p = p.rename(columns={"floors_above": "floors_part"})
    web = p.to_crs(4326)
    web["geometry"] = web.geometry.set_precision(10 ** (-precision))
    web = web.replace({np.nan: None})
    path = out_dir / "parts.geojson"
    path.write_text(web.to_json(drop_id=True), encoding="utf-8")
    return path
