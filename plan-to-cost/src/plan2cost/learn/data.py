"""Cache CubiCasa5k plans as small, fixed-size arrays so training never touches PNG/SVG.

Each plan becomes one grayscale image and two masks (walls, interior), letterboxed to
`size` x `size`: scaled so the longest side fits, padded with white (image) / 0 (masks).
Decoding images and rasterising SVGs is the slow part, so it is done once, in parallel.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from plan2cost.eval import cubicasa as cc


def letterbox(arr: np.ndarray, size: int, fill: int) -> np.ndarray:
    """Put `arr` (longest side already `size`) top-left on a size x size canvas."""
    canvas = np.full((size, size), fill, arr.dtype)
    canvas[: arr.shape[0], : arr.shape[1]] = arr
    return canvas


def load_plan(plan_dir: Path, size: int) -> tuple[np.ndarray, np.ndarray]:
    """(image uint8 [size,size], masks uint8 [2,size,size]) for one plan."""
    image, k = cc.read_image(plan_dir / "F1_scaled.png", size)
    gray = image if image.ndim == 2 else cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    wall, interior = cc.label_masks(plan_dir / "model.svg", gray.shape, k)
    return (
        letterbox(gray, size, 255),
        np.stack(
            [
                letterbox(wall.astype(np.uint8), size, 0),
                letterbox(interior.astype(np.uint8), size, 0),
            ]
        ),
    )


def _load(args: tuple[Path, int]):
    try:
        return load_plan(*args)
    except Exception:  # a broken plan is skipped, and counted by the caller
        return None


def build_cache(root: Path, split: str, size: int, out: Path, workers: int = 8) -> dict:
    plans = cc.load_split(root, split)
    with ProcessPoolExecutor(workers) as pool:
        loaded = list(pool.map(_load, [(p, size) for p in plans], chunksize=8))
    ok = [(p, r) for p, r in zip(plans, loaded, strict=True) if r is not None]
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        x=np.stack([r[0] for _, r in ok]),
        y=np.stack([r[1] for _, r in ok]),
        ids=np.array([f"{p.parent.name}/{p.name}" for p, _ in ok]),
    )
    return {"split": split, "n": len(ok), "skipped": len(plans) - len(ok), "size": size}


def augment(
    x: np.ndarray, y: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Random flips and 90-degree turns (a plan is still a plan), plus a mild contrast change."""
    k = int(rng.integers(4))
    x, y = np.rot90(x, k, (-2, -1)), np.rot90(y, k, (-2, -1))
    if rng.random() < 0.5:
        x, y = x[..., ::-1], y[..., ::-1]
    gain = rng.uniform(0.8, 1.2)
    x = np.clip((x.astype(np.float32) - 128) * gain + 128, 0, 255)
    return np.ascontiguousarray(x), np.ascontiguousarray(y)


def main(argv: list[str] | None = None) -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Cache CubiCasa5k splits as small arrays.")
    ap.add_argument("--root", type=Path, required=True, help="…/extracted/cubicasa5k")
    ap.add_argument("--out", type=Path, required=True, help="directory for <split>.npz files")
    ap.add_argument("--size", type=int, default=384)
    ap.add_argument("--splits", nargs="+", default=["val", "test", "train"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    for split in a.splits:
        print(
            json.dumps(build_cache(a.root, split, a.size, a.out / f"{split}.npz", a.workers)),
            flush=True,
        )


if __name__ == "__main__":
    main()
