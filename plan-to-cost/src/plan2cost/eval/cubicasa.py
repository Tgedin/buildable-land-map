"""Evaluate the vision baseline on CubiCasa5k (CC BY-NC-SA 4.0, never committed).

Label frame: the SVG polygon coordinates are pixel coordinates of `F1_scaled.png`, with no
scaling or offset (this is how the dataset's own loader uses them, floortrans/loaders/
house.py). The SVG's width/height attributes are NOT the image size. An earlier version of
this module scaled the polygons by those attributes and wrongly concluded the labels were
unaligned (corrected in ADR 0002).

Both image and labels are then scaled together by one factor so the longest side is
`work_dim` pixels. Walls = SVG polygons of class "Wall" (direct children only, so nested
windows and doors are excluded); interior = class "Space" except "Outdoor".

Metrics per plan: intersection-over-union (IoU), precision and recall of the wall mask, and
IoU of the interior (room) mask.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

from plan2cost.vision import rooms, walls

WORK_DIM = 1000  # longest side, in pixels, for both image and labels


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


def label_masks(
    svg_path: Path, shape: tuple[int, int], scale: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """(wall mask, interior mask) of size `shape` = (height, width) of the scaled image.

    `scale` is the factor the image was resized by (the polygons live in the unscaled frame).
    """
    root = ET.parse(svg_path).getroot()
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
            cv2.fillPoly(target, [np.round(poly * scale).astype(np.int32)], 1)
    return wall.astype(bool), interior.astype(bool)


def read_image(path: Path, work_dim: int = WORK_DIM) -> tuple[np.ndarray, float]:
    """Image resized so its longest side is work_dim, and the factor used."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"cannot read image {path}")
    k = work_dim / max(img.shape[:2])
    return cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA), k


def overlap(pred: np.ndarray, gt: np.ndarray) -> dict[str, float]:
    """IoU, precision and recall of two boolean masks. Empty cases give 0.0, not NaN."""
    inter = float((pred & gt).sum())
    union = float((pred | gt).sum())
    return {
        "iou": inter / union if union else 0.0,
        "precision": inter / pred.sum() if pred.any() else 0.0,
        "recall": inter / gt.sum() if gt.any() else 0.0,
    }


def evaluate_plan(plan_dir: Path, close_frac: float = 0.0, work_dim: int = WORK_DIM) -> dict:
    image, k = read_image(plan_dir / "F1_scaled.png", work_dim)
    gt_wall, gt_interior = label_masks(plan_dir / "model.svg", image.shape[:2], k)

    pred_wall = walls.wall_mask(walls.to_gray(image), close_frac=close_frac)
    pred_interior = rooms.interior_mask(pred_wall)
    w, r = overlap(pred_wall, gt_wall), overlap(pred_interior, gt_interior)
    return {
        "id": plan_dir.name,
        "style": plan_dir.parent.name,
        "detected": bool(pred_interior.any()),
        "wall_iou": w["iou"],
        "wall_precision": w["precision"],
        "wall_recall": w["recall"],
        "interior_iou": r["iou"],
    }


def load_split(root: Path, split: str) -> list[Path]:
    lines = (root / f"{split}.txt").read_text().split()
    return [root / line.strip("/") for line in lines]


def summarize(results: list[dict]) -> dict:
    if not results:
        return {"n_plans": 0}  # nothing evaluated: say so rather than report NaN statistics

    def col(key: str) -> np.ndarray:
        return np.array([r[key] for r in results])

    out = {
        "n_plans": len(results),
        "detected_share": round(float(col("detected").mean()), 3),
        "wall_iou_median": round(float(np.median(col("wall_iou"))), 3),
        "wall_iou_mean": round(float(col("wall_iou").mean()), 3),
        "wall_precision_mean": round(float(col("wall_precision").mean()), 3),
        "wall_recall_mean": round(float(col("wall_recall").mean()), 3),
        "interior_iou_median": round(float(np.median(col("interior_iou"))), 3),
        "interior_iou_mean": round(float(col("interior_iou").mean()), 3),
        "interior_iou_ge_0.5_share": round(float((col("interior_iou") >= 0.5).mean()), 3),
    }
    out["by_style"] = {
        style: {
            "n": len(group),
            "wall_iou_mean": round(float(np.mean([r["wall_iou"] for r in group])), 3),
            "interior_iou_mean": round(float(np.mean([r["interior_iou"] for r in group])), 3),
        }
        for style in sorted({r["style"] for r in results})
        for group in [[r for r in results if r["style"] == style]]
    }
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, required=True, help="…/extracted/cubicasa5k")
    ap.add_argument("--split", default="test", choices=["train", "val", "test"])
    ap.add_argument("--limit", type=int, default=0, help="first N plans only (0 = all)")
    ap.add_argument("--close-frac", type=float, default=0.0, help="wall_mask close_frac")
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
