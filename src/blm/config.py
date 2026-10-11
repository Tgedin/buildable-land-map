"""Typed access to config/area.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CatastroConfig:
    tile_size_m: float = 500
    max_features_per_request: int = 5000
    timeout_s: int = 60


@dataclass(frozen=True)
class LidarConfig:
    ground_class: int = 2
    building_class: int = 6
    inner_buffer_m: float = 0.5
    ground_ring_m: float = 10.0
    min_roof_points: int = 20


@dataclass(frozen=True)
class PlanningConfig:
    """Municipal plan (PGOU) layer. `alignments_url` None = no plan data for this area."""

    alignments_url: str | None = None  # ArcGIS REST layer URL (…/MapServer/<id>)
    ground_floor_offset: int = 1  # allowed floors = plan `altura` + this (ASSUMPTION, ADR 0004)
    protected_min_share: float = 0.5  # share of parcel under protected polygons => protected
    min_coverage: float = 0.5  # share of parcel that must carry a numeric height
    timeout_s: int = 60


@dataclass(frozen=True)
class MetricsConfig:
    floor_height_m: float = 3.0
    neighbor_radius_m: float = 50.0
    min_neighbors: int = 3


@dataclass(frozen=True)
class ExportConfig:
    coordinate_precision: int = 6


@dataclass(frozen=True)
class AreaConfig:
    name: str
    label: str
    epsg: int
    bbox: tuple[float, float, float, float]
    catastro: CatastroConfig = field(default_factory=CatastroConfig)
    lidar: LidarConfig = field(default_factory=LidarConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    planning: PlanningConfig = field(default_factory=PlanningConfig)
    export: ExportConfig = field(default_factory=ExportConfig)

    @property
    def crs(self) -> str:
        return f"EPSG:{self.epsg}"

    # Standard data locations, all relative to the repo root.
    @property
    def raw_dir(self) -> Path:
        return REPO_ROOT / "data" / "raw"

    @property
    def interim_dir(self) -> Path:
        return REPO_ROOT / "data" / "interim" / self.name

    @property
    def processed_dir(self) -> Path:
        return REPO_ROOT / "data" / "processed" / self.name

    @property
    def web_data_dir(self) -> Path:
        return REPO_ROOT / "web" / "data"


def load_config(path: str | Path = REPO_ROOT / "config" / "area.yaml") -> AreaConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    bbox = tuple(float(v) for v in raw["bbox"])
    if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError(f"bbox must be [xmin, ymin, xmax, ymax], got {raw['bbox']}")
    return AreaConfig(
        name=raw["name"],
        label=raw.get("label", raw["name"]),
        epsg=int(raw["epsg"]),
        bbox=bbox,  # type: ignore[arg-type]
        catastro=CatastroConfig(**raw.get("catastro", {})),
        lidar=LidarConfig(**raw.get("lidar", {})),
        metrics=MetricsConfig(**raw.get("metrics", {})),
        planning=PlanningConfig(**raw.get("planning", {})),
        export=ExportConfig(**raw.get("export", {})),
    )
