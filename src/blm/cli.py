"""Command line entry point.

blm fetch     Catastro WFS            -> data/interim/<area>/parts.parquet
blm heights   + PNOA LiDAR .laz       -> data/interim/<area>/parts_lidar.parquet
blm plan      municipal plan (PGOU)   -> data/interim/<area>/pgou.parquet + zoning.parquet
blm lidar     download the .laz sheets -> data/raw/lidar/ (if the config has a sheet index)
blm candidates only the parcels a screening.json lists -> web data dir (city scale, ADR 0006)
blm build     parcels + gap + checks  -> data/processed/<area>/ + web/data/
blm run       fetch -> heights (if .laz present) -> build
blm sample    synthetic data end-to-end, so the map works offline
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import geopandas as gpd

from blm import catastro, export, lidar, lidar_sheets, metrics, planning, synthetic
from blm.config import REPO_ROOT, AreaConfig, load_config

log = logging.getLogger("blm")


def _parts_path(cfg: AreaConfig) -> Path:
    return cfg.interim_dir / "parts.parquet"


def _parts_lidar_path(cfg: AreaConfig) -> Path:
    return cfg.interim_dir / "parts_lidar.parquet"


def cmd_fetch(cfg: AreaConfig, args: argparse.Namespace) -> None:
    if args.from_files:
        parts = catastro.load_from_files([Path(p) for p in args.from_files], cfg.crs)
    else:
        parts = catastro.fetch_building_parts(cfg)
        parts["current_use"] = parts["refcat"].map(catastro.fetch_building_uses(cfg))
    cfg.interim_dir.mkdir(parents=True, exist_ok=True)
    parts.to_parquet(_parts_path(cfg))
    log.info(
        "Saved %d building parts (%d parcels) -> %s",
        len(parts),
        parts["refcat"].nunique(),
        _parts_path(cfg),
    )


def _pgou_path(cfg: AreaConfig) -> Path:
    return cfg.interim_dir / "pgou.parquet"


def _zoning_path(cfg: AreaConfig) -> Path:
    return cfg.interim_dir / "zoning.parquet"


def cmd_plan(cfg: AreaConfig, args: argparse.Namespace) -> None:
    alignments = planning.fetch_alignments(cfg)
    cfg.interim_dir.mkdir(parents=True, exist_ok=True)
    alignments.to_parquet(_pgou_path(cfg))
    log.info(
        "Saved %d plan polygons (%s) -> %s",
        len(alignments),
        alignments["kind"].value_counts().to_dict(),
        _pgou_path(cfg),
    )
    if cfg.planning.zoning_url:
        zoning = planning.fetch_zoning(cfg)
        zoning.to_parquet(_zoning_path(cfg))
        log.info("Saved %d zone polygons -> %s", len(zoning), _zoning_path(cfg))


def cmd_candidates(cfg: AreaConfig, args: argparse.Namespace) -> None:
    """Export only the parcels listed in a screening.json (written by plan2cost.screen_map)."""
    screening = json.loads(Path(args.screening).read_text(encoding="utf-8"))
    refcats = set(screening["parcels"])
    parcels = gpd.read_parquet(cfg.processed_dir / "parcels.parquet")
    summary = json.loads((cfg.processed_dir / "summary.json").read_text())
    out = Path(args.out) if args.out else cfg.web_data_dir
    export.export_candidates(
        parcels, refcats, summary, out, cfg.label, cfg.export.coordinate_precision
    )
    log.info("Exported %d of %d parcels -> %s", len(refcats), len(parcels), out)


def cmd_lidar(cfg: AreaConfig, args: argparse.Namespace) -> None:
    paths = lidar_sheets.download_sheets(cfg, cfg.raw_dir / "lidar")
    log.info("LiDAR sheets ready: %s", ", ".join(p.name for p in paths))


def _laz_files(cfg: AreaConfig) -> list[Path]:
    lidar_dir = cfg.raw_dir / "lidar"
    return sorted([*lidar_dir.glob("*.laz"), *lidar_dir.glob("*.las")])


def cmd_heights(cfg: AreaConfig, args: argparse.Namespace) -> None:
    files = _laz_files(cfg)
    if not files:
        sys.exit(f"No .laz/.las files in {cfg.raw_dir / 'lidar'}. See docs/data-sources.md.")
    parts = gpd.read_parquet(_parts_path(cfg))
    xmin, ymin, xmax, ymax = parts.total_bounds
    pad = cfg.lidar.ground_ring_m + 1
    pc = lidar.read_laz(
        files,
        (xmin - pad, ymin - pad, xmax + pad, ymax + pad),
        keep={cfg.lidar.ground_class, cfg.lidar.building_class},
    )
    log.info("Point cloud: %d points", len(pc))
    out = lidar.building_heights(parts, pc, cfg.lidar)
    out.to_parquet(_parts_lidar_path(cfg))
    log.info(
        "Heights for %d parts, %d high confidence -> %s",
        out["lidar_height_m"].notna().sum(),
        (out["lidar_confidence"] == "high").sum(),
        _parts_lidar_path(cfg),
    )


def _build(cfg: AreaConfig, parts: gpd.GeoDataFrame, synthetic_data: bool = False) -> dict:
    parcels = metrics.aggregate_parcels(parts)
    parcels = metrics.buildable_gap(parcels, cfg.metrics)
    if not synthetic_data and _pgou_path(cfg).exists():
        alignments = gpd.read_parquet(_pgou_path(cfg))
        parcels = planning.match_parcels(parcels, alignments, cfg.planning)
        if _zoning_path(cfg).exists():
            parcels = planning.match_zone(parcels, gpd.read_parquet(_zoning_path(cfg)))
        parcels = metrics.plan_gap(parcels)
    else:
        log.warning("No plan data (run `blm plan`): building the neighbour comparison only.")
    validation = metrics.validate_lidar(parts, cfg.metrics)
    summary = metrics.summarize(parcels, validation)

    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    parcels.to_parquet(cfg.processed_dir / "parcels.parquet")
    (cfg.processed_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    export.export_web(
        parcels,
        summary,
        cfg.web_data_dir,
        cfg.label,
        cfg.export.coordinate_precision,
        synthetic=synthetic_data,
    )
    log.info("Summary: %s", json.dumps(summary))
    return summary


def cmd_build(cfg: AreaConfig, args: argparse.Namespace) -> None:
    src = _parts_lidar_path(cfg) if _parts_lidar_path(cfg).exists() else _parts_path(cfg)
    if not src.exists():
        sys.exit("No building parts found. Run `blm fetch` first.")
    log.info("Building from %s", src.name)
    _build(cfg, gpd.read_parquet(src))


def cmd_run(cfg: AreaConfig, args: argparse.Namespace) -> None:
    cmd_fetch(cfg, args)
    if cfg.planning.alignments_url:
        cmd_plan(cfg, args)
    if cfg.lidar.sheet_index_url:
        cmd_lidar(cfg, args)
    if _laz_files(cfg):
        cmd_heights(cfg, args)
    else:
        log.warning("No LiDAR tiles found, building without heights.")
        _parts_lidar_path(cfg).unlink(missing_ok=True)
    cmd_build(cfg, args)


def cmd_sample(cfg: AreaConfig, args: argparse.Namespace) -> None:
    parts = synthetic.make_parts(crs=cfg.crs)
    pc = synthetic.make_point_cloud(parts)
    parts = lidar.building_heights(parts, pc, cfg.lidar)
    sample_cfg = AreaConfig(
        name="synthetic-sample",
        label="Synthetic sample (not real data)",
        epsg=cfg.epsg,
        bbox=cfg.bbox,
        lidar=cfg.lidar,
        metrics=cfg.metrics,
        export=cfg.export,
    )
    _build(sample_cfg, parts, synthetic_data=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="blm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "area.yaml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="download Catastro building parts")
    p_fetch.add_argument(
        "--from-files",
        nargs="+",
        metavar="GML",
        help="parse saved WFS responses instead of calling the service",
    )
    sub.add_parser("heights", help="compute LiDAR heights per building part")
    sub.add_parser("plan", help="download municipal plan (PGOU) heights")
    sub.add_parser("lidar", help="download the LiDAR sheets covering the area")
    p_cand = sub.add_parser("candidates", help="export only the parcels in a screening.json")
    p_cand.add_argument(
        "--screening", required=True, help="screening.json from plan2cost.screen_map"
    )
    p_cand.add_argument("--out", help="output directory (default: the area's web data dir)")
    sub.add_parser("build", help="parcels, buildable gap, validation, web export")
    p_run = sub.add_parser("run", help="fetch -> heights -> build")
    p_run.add_argument("--from-files", nargs="+", metavar="GML")
    sub.add_parser("sample", help="synthetic end-to-end run (offline)")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    cfg = load_config(args.config)
    {
        "fetch": cmd_fetch,
        "heights": cmd_heights,
        "plan": cmd_plan,
        "lidar": cmd_lidar,
        "candidates": cmd_candidates,
        "build": cmd_build,
        "run": cmd_run,
        "sample": cmd_sample,
    }[args.command](cfg, args)


if __name__ == "__main__":
    main()
