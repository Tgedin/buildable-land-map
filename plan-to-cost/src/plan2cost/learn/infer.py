"""Run a trained U-Net on one plan image and return masks at the image's own size."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch

from plan2cost.learn.data import letterbox
from plan2cost.learn.model import UNet
from plan2cost.learn.train import to_input


def load_model(path: Path) -> UNet:
    """Model in eval mode. The input size is not stored in the checkpoint: pass it to predict."""
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    model = UNet(base=ckpt["base"])
    model.load_state_dict(ckpt["state"])
    return model.eval()


@torch.no_grad()
def predict_masks(model: UNet, gray: np.ndarray, size: int) -> tuple[np.ndarray, np.ndarray]:
    """(wall mask, interior mask), both boolean and the same shape as `gray`."""
    h, w = gray.shape
    k = size / max(h, w)
    rh, rw = max(1, round(h * k)), max(1, round(w * k))
    small = cv2.resize(gray, (rw, rh), interpolation=cv2.INTER_AREA)
    canvas = letterbox(small, size, 255)
    logits = model(to_input(canvas[None]))[0].numpy()  # [2, size, size]
    crop = logits[:, :rh, :rw]  # drop the padding the network saw
    wall = cv2.resize(crop[0], (w, h), interpolation=cv2.INTER_LINEAR) > 0
    interior = cv2.resize(crop[1], (w, h), interpolation=cv2.INTER_LINEAR) > 0
    return wall, interior
