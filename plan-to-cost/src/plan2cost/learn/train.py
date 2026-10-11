"""Train the U-Net on the cached arrays. CPU-friendly: bf16 autocast, channels_last."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from plan2cost.learn import data
from plan2cost.learn.model import UNet, n_params


def to_input(x: np.ndarray) -> torch.Tensor:
    """uint8/float plan [B,H,W] -> float tensor [B,1,H,W], 0 = white paper, 1 = black ink."""
    t = torch.from_numpy(np.asarray(x, dtype=np.float32))
    return (1.0 - t / 255.0).unsqueeze(1)


def dice_bce(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    bce = nn.functional.binary_cross_entropy_with_logits(logits, target)
    p = torch.sigmoid(logits)
    inter = (p * target).sum((0, 2, 3))
    dice = 1 - (2 * inter + 1) / (p.sum((0, 2, 3)) + target.sum((0, 2, 3)) + 1)
    return bce + dice.mean()


@torch.no_grad()
def iou_per_channel(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    pred = logits > 0
    t = target > 0.5
    inter = (pred & t).sum((0, 2, 3)).float()
    union = (pred | t).sum((0, 2, 3)).float()
    return inter / union.clamp(min=1)


def pick_device(name: str = "auto") -> torch.device:
    """'auto' = the GPU if there is one, else the CPU."""
    if name == "auto":
        name = "cuda" if torch.cuda.is_available() else "cpu"
    return torch.device(name)


def autocast(device: torch.device):
    """Mixed precision: fp16 on a GPU (a Colab T4 has no fast bf16), bf16 on this CPU."""
    dtype = torch.float16 if device.type == "cuda" else torch.bfloat16
    return torch.autocast(device.type, dtype=dtype)


def evaluate(
    model: nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch: int = 16,
    device: torch.device | None = None,
) -> dict:
    device = device or torch.device("cpu")
    model.eval()
    inter = np.zeros(2)
    union = np.zeros(2)
    with torch.no_grad(), autocast(device):
        for i in range(0, len(x), batch):
            xb = to_input(x[i : i + batch]).to(device).contiguous(memory_format=torch.channels_last)
            pred = model(xb).float() > 0
            t = torch.from_numpy(y[i : i + batch]).to(device) > 0
            inter += (pred & t).sum((0, 2, 3)).cpu().numpy()
            union += (pred | t).sum((0, 2, 3)).cpu().numpy()
    wall, interior = (inter / np.maximum(union, 1)).tolist()
    return {"wall_iou": wall, "interior_iou": interior}  # pooled over pixels, not per plan


def train(
    cache: Path,
    out: Path,
    epochs: int,
    batch: int,
    base: int,
    lr: float,
    threads: int,
    seed: int,
    limit: int = 0,
    device: str = "cpu",
):
    dev = pick_device(device)
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    tr, va = np.load(cache / "train.npz"), np.load(cache / "val.npz")
    xt, yt, xv, yv = tr["x"], tr["y"], va["x"], va["y"]
    if limit:  # smoke tests: a few plans, same code path
        xt, yt, xv, yv = xt[:limit], yt[:limit], xv[:limit], yv[:limit]
    model = UNet(base=base).to(dev, memory_format=torch.channels_last)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scaler = torch.amp.GradScaler(dev.type, enabled=dev.type == "cuda")  # fp16 needs loss scaling
    steps = epochs * (len(xt) // batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps)
    print(
        f"params {n_params(model):,}  train {len(xt)}  val {len(xv)}  device {dev}  "
        f"threads {threads}",
        flush=True,
    )

    best, log = -1.0, []
    out.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, epochs + 1):
        model.train()
        t0, total = time.time(), 0.0
        order = rng.permutation(len(xt))
        for s in range(len(xt) // batch):
            idx = order[s * batch : (s + 1) * batch]
            pairs = [data.augment(xt[i], yt[i], rng) for i in idx]
            x = (
                to_input(np.stack([p[0] for p in pairs]))
                .to(dev)
                .contiguous(memory_format=torch.channels_last)
            )
            y = torch.from_numpy(np.stack([p[1] for p in pairs])).float().to(dev)
            with autocast(dev):
                logits = model(x)
            loss = dice_bce(logits.float(), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
        m = evaluate(model, xv, yv, device=dev)
        score = m["wall_iou"] + m["interior_iou"]
        rec = {
            "epoch": epoch,
            "loss": total / (len(xt) // batch),
            "secs": round(time.time() - t0, 1),
            **m,
        }
        log.append(rec)
        print(json.dumps(rec), flush=True)
        if score > best:
            best = score
            state = {k: v.cpu() for k, v in model.state_dict().items()}  # loadable anywhere
            torch.save({"state": state, "base": base, "val": m, "epoch": epoch}, out)
    return log


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--base", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="use only the first N plans (smoke test)")
    ap.add_argument("--device", default="cpu", help="cpu, cuda or auto (GPU if there is one)")
    a = ap.parse_args(argv)
    train(a.cache, a.out, a.epochs, a.batch, a.base, a.lr, a.threads, a.seed, a.limit, a.device)


if __name__ == "__main__":
    main()
