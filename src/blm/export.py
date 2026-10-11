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
