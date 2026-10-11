"""Parcel aggregation, LiDAR validation and the buildable-gap heuristic.

Buildable gap (v0.2, NOT zoning):
    dominant_floors  = median floors of neighbouring parcels within R metres
    gap_floors       = max(0, dominant_floors − parcel floors)   (floors of its tallest part)
    gap_m2           = main_footprint_m2 × gap_floors

main_footprint_m2 is the footprint of the parts at the parcel's tallest height, i.e. the
building body. Low rear annexes are ignored on purpose: in Ruzafa, 1-floor workshops fill
inner courtyards, and v0 counted "5 missing floors" there (687,618 m², 811 of 932 parcels).
Courtyards are not buildable, so the gap now means "add storeys to the main body"
(docs/decisions/0003-gap-main-body.md).

It answers "how much floor area is missing compared with the street around it",
which is a proxy for under-use. Real buildability depends on the municipal plan.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from blm.config import MetricsConfig


def aggregate_parcels(parts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """One row per cadastral parcel (refcat)."""
    p = parts.copy()
    p["floors_above"] = p["floors_above"].fillna(0)
    p["existing_m2"] = p["footprint_m2"] * p["floors_above"]
    has_lidar = "lidar_height_m" in p.columns

    agg = {
        "floors_above": "max",
        "existing_m2": "sum",
        "part_id": "count",
    }
    if has_lidar:
        agg["lidar_height_m"] = "max"

    parcels = p.dissolve(by="refcat", aggfunc=agg).reset_index()
    parcels = parcels.rename(columns={"floors_above": "floors", "part_id": "n_parts"})
    parcels["footprint_m2"] = parcels.geometry.area.round(1)
    top = p["floors_above"] == p.groupby("refcat")["floors_above"].transform("max")
    main_fp = p[top].groupby("refcat")["footprint_m2"].sum()
    parcels["main_footprint_m2"] = parcels["refcat"].map(main_fp).round(1)
    parcels["existing_m2"] = parcels["existing_m2"].round(1)
    if has_lidar:
        conf = p.groupby("refcat")["lidar_confidence"].agg(
            lambda s: "high" if (s == "high").all() else "low"
        )
        parcels["lidar_confidence"] = parcels["refcat"].map(conf)
    return parcels


def buildable_gap(parcels: gpd.GeoDataFrame, cfg: MetricsConfig) -> gpd.GeoDataFrame:
    out = parcels.copy()
    centroids = out.geometry.centroid.values
    tree = shapely.STRtree(centroids)
    pairs = tree.query(centroids, predicate="dwithin", distance=cfg.neighbor_radius_m)
    src, nbr = pairs
    keep = src != nbr
    src, nbr = src[keep], nbr[keep]

    floors = out["floors"].to_numpy(dtype=float)
    dominant = np.full(len(out), np.nan)
    n_neighbors = np.zeros(len(out), dtype=int)
    if len(src):
        df = pd.DataFrame({"src": src, "f": floors[nbr]})
        df = df[df["f"] > 0]  # ignore empty lots/sheds when defining the street height
        g = df.groupby("src")["f"]
        med, cnt = g.median(), g.size()
        dominant[med.index.to_numpy()] = med.to_numpy()
        n_neighbors[cnt.index.to_numpy()] = cnt.to_numpy()

    valid = n_neighbors >= cfg.min_neighbors
    dominant = np.where(valid, np.round(dominant), np.nan)
    gap_floors = np.clip(dominant - floors, 0, None)

    out["dominant_floors"] = dominant
    out["n_neighbors"] = n_neighbors
    out["gap_floors"] = gap_floors
    out["gap_m2"] = np.round(out["main_footprint_m2"].to_numpy() * gap_floors, 0)
    return out


def validate_lidar(parts: gpd.GeoDataFrame, cfg: MetricsConfig) -> dict:
    """Compare LiDAR-derived floors with Catastro floors (high-confidence parts only)."""
    if "lidar_height_m" not in parts.columns:
        return {"n": 0}
    p = parts[
        (parts["lidar_confidence"] == "high")
        & parts["lidar_height_m"].notna()
        & (parts["floors_above"].fillna(0) >= 1)
    ]
    if p.empty:
        return {"n": 0}
    lidar_floors = np.round(p["lidar_height_m"] / cfg.floor_height_m)
    err = lidar_floors - p["floors_above"]
    return {
        "n": int(len(p)),
        "mae_floors": round(float(err.abs().mean()), 3),
        "bias_floors": round(float(err.mean()), 3),
        "share_exact": round(float((err == 0).mean()), 3),
        "share_within_1": round(float((err.abs() <= 1).mean()), 3),
        "median_m_per_floor": round(float((p["lidar_height_m"] / p["floors_above"]).median()), 2),
    }


def summarize(parcels: gpd.GeoDataFrame, validation: dict) -> dict:
    with_gap = parcels[parcels["gap_m2"] > 0]
    return {
        "n_parcels": int(len(parcels)),
        "n_parcels_with_gap": int(len(with_gap)),
        "total_gap_m2": float(parcels["gap_m2"].fillna(0).sum()),
        "total_existing_m2": float(parcels["existing_m2"].sum()),
        "lidar_validation": validation,
    }
