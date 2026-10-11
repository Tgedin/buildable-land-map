"""Evaluate the vision baseline on CubiCasa5k (CC BY-NC-SA 4.0, never committed).

Why scale-free measures: in CubiCasa5k the SVG labels are NOT pixel-aligned with the images
(checked on 60 test plans: every simple scaling convention puts only ~10% of labelled wall
pixels on dark pixels). A pixel IoU would measure the annotation offset, not our detector.
So we compare quantities that do not depend on the pixel frame:

    detected      did the baseline find at least one enclosed room?
    wall_ratio    wall centre-line length / sqrt(interior area)   (dimensionless)

The label side comes from the SVG polygons (class "Wall" and class "Space", except
"Outdoor"); the prediction side from the image, resized to the same working size.
This says how well the *shape* of the plan is read. It says nothing yet about absolute
areas, which also need a scale (see vision/quantities.py).
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

from plan2cost.vision import quantities, rooms, walls

WORK_DIM = 1000  # longest side, in pixels, for both label and image


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _polygons(group: ET.Element) -> list[np.ndarray]:
    """Polygons that are direct children of `group` (nested windows/doors are skipped)."""
    out = []
    for child in group:
        if _local(child.tag) == "polygon" and child.get("points"):
            pts = [tuple(map(float, p.split(","))) for p in child.get("points").split()]
            if len(pts) >= 3:
                out.append(np.array(pts))
    return out


def label_masks(svg_path: Path, work_dim: int = WORK_DIM) -> tuple[np.ndarray, np.ndarray]:
    """(wall mask, interior mask) rasterised from the SVG at the working size."""
    root = ET.parse(svg_path).getroot()
    width, height = float(root.get("width")), float(root.get("height"))
    k = work_dim / max(width, height)
    shape = (max(1, round(height * k)), max(1, round(width * k)))
    wall = np.zeros(shape, np.uint8)
    interior = np.zeros(shape, np.uint8)
    for g in root.iter():
        if _local(g.tag) != "g":
            continue
        tokens = (g.get("class") or "").split()
        if "Wall" in tokens:
            target = wall
        elif "Space" in tokens and "Outdoor" not in tokens:
            target = interior
        else:
            continue
        for poly in _polygons(g):
            cv2.fillPoly(target, [np.round(poly * k).astype(np.int32)], 1)
    return wall.astype(bool), interior.astype(bool)


def read_image(path: Path, work_dim: int = WORK_DIM) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"cannot read image {path}")
    k = work_dim / max(img.shape[:2])
    return cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)


def wall_ratio(wall: np.ndarray, interior_px: float) -> float | None:
    """Wall length / sqrt(interior area). None when there is no interior to divide by."""
    if interior_px <= 0:
        return None
    return quantities.wall_length_px(wall) / float(np.sqrt(interior_px))


def evaluate_plan(plan_dir: Path, close_frac: float = 0.0) -> dict:
    gt_wall, gt_interior = label_masks(plan_dir / "model.svg")
    gt_ratio = wall_ratio(gt_wall, float(gt_interior.sum()))

    pred_wall = walls.wall_mask(
        walls.to_gray(read_image(plan_dir / "F1_scaled.png")), close_frac=close_frac
    )
    found = rooms.find_rooms(pred_wall)
    pred_ratio = wall_ratio(pred_wall, rooms.interior_area_px(found))

    rel = None
    if gt_ratio and pred_ratio is not None:
        rel = (pred_ratio - gt_ratio) / gt_ratio
    return {
        "id": plan_dir.name,
        "style": plan_dir.parent.name,
        "detected": bool(found),
        "n_rooms": len(found),
        "gt_wall_ratio": gt_ratio,
        "pred_wall_ratio": pred_ratio,
        "wall_ratio_rel_error": rel,
    }


def load_split(root: Path, split: str) -> list[Path]:
    lines = (root / f"{split}.txt").read_text().split()
    return [root / line.strip("/") for line in lines]


def summarize(results: list[dict]) -> dict:
    if not results:
        return {"n_plans": 0}  # nothing evaluated: say so rather than report NaN statistics
    errs = np.array(
        [r["wall_ratio_rel_error"] for r in results if r["wall_ratio_rel_error"] is not None]
    )
    abs_err = np.abs(errs)
    out = {
        "n_plans": len(results),
        "detected_share": round(float(np.mean([r["detected"] for r in results])), 3),
        "n_with_ratio": int(len(errs)),
    }
    if len(errs):
        out |= {
            "median_abs_rel_error": round(float(np.median(abs_err)), 3),
            "share_within_20pct": round(float((abs_err <= 0.2).mean()), 3),
            "share_within_50pct": round(float((abs_err <= 0.5).mean()), 3),
            "median_signed_rel_error": round(float(np.median(errs)), 3),
        }
    by_style = {}
    for style in sorted({r["style"] for r in results}):
        group = [r for r in results if r["style"] == style]
        by_style[style] = {
            "n": len(group),
            "detected_share": round(float(np.mean([r["detected"] for r in group])), 3),
        }
    out["by_style"] = by_style
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, required=True, help="…/extracted/cubicasa5k")
    ap.add_argument("--split", default="test", choices=["train", "val", "test"])
    ap.add_argument("--limit", type=int, default=0, help="first N plans only (0 = all)")
    ap.add_argument(
        "--close-frac",
        type=float,
        default=0.10,
        help="wall_mask close_frac (0.10 chosen on the val split, see docs/baseline-results.md)",
    )
    ap.add_argument("--out", type=Path, help="write per-plan results + summary as JSON")
    args = ap.parse_args(argv)

    plans = load_split(args.root, args.split)
    plans = plans[: args.limit] if args.limit else plans
    results, failed = [], []
    for plan_dir in plans:
        try:
            results.append(evaluate_plan(plan_dir, args.close_frac))
        except Exception as exc:  # a broken file must not hide the other plans
            failed.append({"id": plan_dir.name, "error": f"{type(exc).__name__}: {exc}"})
    if not results:
        first = failed[0]["error"] if failed else "no plans in the split"
        raise SystemExit(f"No plan could be evaluated ({len(failed)} failed). First error: {first}")
    summary = summarize(results) | {"n_failed_to_read": len(failed)}
    print(json.dumps(summary, indent=2))
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "plans": results, "failed": failed}))


if __name__ == "__main__":
    main()
